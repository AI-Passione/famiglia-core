import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Agent, ActionLog } from '../types';
import { API_BASE } from '../config';

interface TerminalProps {
  agents: Agent[];
  actions: ActionLog[];
}

interface Message {
  id: string;
  type: 'user' | 'agent';
  speaker: string;
  role: string;
  content: string;
  timestamp: Date;
  status?: 'sending' | 'typing' | 'done' | 'error';
  avatar?: string;
}

interface ChatState {
  id: string;
  type: 'channel' | 'dm';
  name: string;
  icon: string;
  messages: Message[];
  isTyping: boolean;
  agent_id?: string;
}

const AGENT_IMAGE_MAP: Record<string, string> = {
  alfredo: '/images/alfredo.png',
  riccardo: '/images/riccardo.png',
  bella: '/images/bella.png',
  rossini: '/images/dr_rossini.png',
  vito: '/images/vito.png',
  tommy: '/images/tommy.png',
  kowalski: '/images/kowalski.png',
  giuseppina: '/images/giuseppina.png',
  don_jimmy: '/images/don_jimmy.png',
};

const AGENT_ROLE_MAP: Record<string, string> = {
  alfredo: 'Strategic Lead',
  riccardo: 'Signal Mechanic',
  bella: 'Social Secretary',
  rossini: 'Research Whisperer',
  vito: 'House Banker',
  tommy: 'Logistics Runner',
  kowalski: 'Systems Scout',
  giuseppina: 'PR & Brand Excellence',
};

interface ChannelDef {
  id: string;
  label: string;
  icon: string;
  description: string;
  agent_id?: string;
  welcome: string;
  agentSpeaker?: string;
}

const STARRED_CHANNELS: ChannelDef[] = [
  { id: 'admin-bella', label: 'admin-bella', icon: '💋', description: 'Admin ops, scheduling & docs', agent_id: 'bella', agentSpeaker: 'Bella', welcome: 'Don Jimmy, your calendar and documents are always in order. How may I assist?' },
  { id: 'alerts', label: 'alerts', icon: '🚨', description: 'System alerts & critical signals', agent_id: 'alfredo', agentSpeaker: 'Alfredo', welcome: 'Don Jimmy, the alert system is live. I will surface only what matters.' },
  { id: 'command-center', label: 'command-center', icon: '🎯', description: 'Alfredo\'s orchestration hub', agent_id: 'alfredo', agentSpeaker: 'Alfredo', welcome: 'Don Jimmy, #command-center is secure. I am standing by for your directives.' },
  { id: 'data-kowalski', label: 'data-kowalski', icon: '📊', description: 'Analytics, BI & data science', agent_id: 'kowalski', agentSpeaker: 'Kowalski', welcome: 'Don Jimmy, the data is ready. What requires analysis?' },
  { id: 'product-rossini', label: 'product-rossini', icon: '🔬', description: 'Product strategy & market research', agent_id: 'rossini', agentSpeaker: 'Dr. Rossini', welcome: 'Don Jimmy, I have been monitoring the market signals. What requires investigation?' },
  { id: 'research-insights', label: 'research-insights', icon: '✨', description: 'Research insights & intelligence briefs', agent_id: 'rossini', agentSpeaker: 'Dr. Rossini', welcome: 'Don Jimmy, the latest intelligence is compiled and ready for your review.' },
  { id: 'tech-riccado', label: 'tech-riccado', icon: '🔧', description: 'Code reviews, DevOps & engineering', agent_id: 'riccado', agentSpeaker: 'Riccardo', welcome: 'Don Jimmy, the codebase is under my watch. What needs to be fixed or built?' },
];

const ALL_CHANNELS: ChannelDef[] = [
  { id: '_dev', label: '_dev', icon: '🛠️', description: 'Internal dev sandbox & experiments', agent_id: 'riccado', agentSpeaker: 'Riccardo', welcome: 'Don Jimmy, dev sandbox is active.' },
  { id: 'agents-coordination', label: 'agents-coordination', icon: '🤝', description: 'Multi-agent workflow coordination', agent_id: 'alfredo', agentSpeaker: 'Alfredo', welcome: 'Don Jimmy, the agents are coordinated and awaiting orders.' },
  { id: 'all-la-passione-inc', label: 'all-la-passione-inc', icon: '🏛️', description: 'Family-wide announcements', agent_id: 'alfredo', agentSpeaker: 'Alfredo', welcome: 'Don Jimmy, the entire Famiglia is listening.' },
  { id: 'social', label: 'social', icon: '📢', description: 'PR, brand & social strategy', agent_id: 'giuseppina', agentSpeaker: 'Giuseppina', welcome: 'Don Jimmy, the brand is spotless and the audience is ready. Shall we make some noise?' },
];

function buildInitialChats(): Record<string, ChatState> {
  const result: Record<string, ChatState> = {};
  [...STARRED_CHANNELS, ...ALL_CHANNELS].forEach(ch => {
    result[ch.id] = {
      id: ch.id,
      type: 'channel',
      name: ch.label,
      icon: ch.icon,
      messages: ch.agentSpeaker ? [{
        id: `init-${ch.id}`,
        type: 'agent',
        speaker: ch.agentSpeaker,
        role: AGENT_ROLE_MAP[ch.agent_id?.toLowerCase() || ''] || 'Agent',
        content: ch.welcome,
        timestamp: new Date(),
        status: 'done',
        avatar: AGENT_IMAGE_MAP[ch.agent_id?.toLowerCase() || '']
      }] : [],
      isTyping: false,
      agent_id: ch.agent_id
    };
  });
  return result;
}

export function Terminal({ agents, actions }: TerminalProps) {
  const [activeChatId, setActiveChatId] = useState<string>('command-center');
  const [chats, setChats] = useState<Record<string, ChatState>>(buildInitialChats);

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const activeChat = chats[activeChatId];

  // Sync agents-coordination with live action feed
  useEffect(() => {
    if (activeChatId === 'agents-coordination' && actions.length > 0) {
      const opMessages: Message[] = actions.slice(0, 20).map(action => ({
        id: `op-${action.id}`,
        type: 'agent' as const,
        speaker: action.agent_name,
        role: AGENT_ROLE_MAP[action.agent_name.toLowerCase()] || 'Agent',
        content: `Acknowledged: ${action.action_type.replace(/_/g, ' ')}. Status: ${action.approval_status || 'Executing'}`,
        timestamp: new Date(action.timestamp),
        status: 'done' as const,
        avatar: AGENT_IMAGE_MAP[action.agent_name.toLowerCase()]
      }));
      setChats(prev => ({
        ...prev,
        'agents-coordination': { ...prev['agents-coordination'], messages: opMessages }
      }));
    }
  }, [actions, activeChatId]);

  // Sync all-la-passione-inc with ambient agent pulses
  useEffect(() => {
    if (activeChatId === 'all-la-passione-inc' && agents.length > 0) {
      const AMBIENT_LINES: Record<string, string> = {
        alfredo: 'The Famiglia is coordinated. Everything is moving with understated elegance.',
        riccado: 'Codebase is stable. I have already fixed three things nobody noticed were broken.',
        bella: 'All schedules updated and notes filed. The week looks well-organised, Don Jimmy.',
        rossini: 'Market signals are quiet but telling. I will have a brief ready shortly.',
        vito: 'Financial posture is sound. I am watching two positions with cautious optimism.',
        tommy: 'All operations are executing cleanly. No blockers to report.',
        kowalski: 'Weekly metrics processed. The numbers are holding their patterns.',
        giuseppina: 'Brand presence is immaculate. The noise is tasteful and on-strategy.',
      };
      const ambientMessages: Message[] = agents
        .filter(a => a.status === 'thinking' || a.status === 'idle')
        .slice(0, 5)
        .map(agent => ({
          id: `ambient-${agent.name}`,
          type: 'agent' as const,
          speaker: agent.name,
          role: AGENT_ROLE_MAP[agent.name.toLowerCase()] || 'Agent',
          content: AMBIENT_LINES[agent.name.toLowerCase()] || 'Standing by.',
          timestamp: new Date(agent.last_active || Date.now()),
          status: 'done' as const,
          avatar: AGENT_IMAGE_MAP[agent.name.toLowerCase()]
        }));
      setChats(prev => ({
        ...prev,
        'all-la-passione-inc': { ...prev['all-la-passione-inc'], messages: ambientMessages }
      }));
    }
  }, [agents, activeChatId]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [activeChat.messages, activeChat.isTyping, scrollToBottom]);

  const handleSend = async () => {
    if (!input.trim() || activeChat.isTyping) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      speaker: 'Don Jimmy',
      role: 'Boss',
      content: input,
      timestamp: new Date(),
      status: 'done',
      avatar: AGENT_IMAGE_MAP.don_jimmy
    };

    setChats(prev => ({
      ...prev,
      [activeChatId]: {
        ...prev[activeChatId],
        messages: [...prev[activeChatId].messages, userMessage]
      }
    }));
    setInput('');

    // Only stream if it's a DM or #directives
    const targetAgentId = activeChat.type === 'dm' ? activeChat.agent_id : (activeChatId === 'directives' ? 'alfredo' : null);
    
    if (!targetAgentId) return;

    setChats(prev => ({
      ...prev,
      [activeChatId]: { ...prev[activeChatId], isTyping: true }
    }));

    const agentMessageId = (Date.now() + 1).toString();
    const newAgentMessage: Message = {
      id: agentMessageId,
      type: 'agent',
      speaker: targetAgentId.charAt(0).toUpperCase() + targetAgentId.slice(1),
      role: AGENT_ROLE_MAP[targetAgentId.toLowerCase()] || 'Agent',
      content: '',
      timestamp: new Date(),
      status: 'typing',
      avatar: AGENT_IMAGE_MAP[targetAgentId.toLowerCase()]
    };
    
    setChats(prev => ({
      ...prev,
      [activeChatId]: {
        ...prev[activeChatId],
        messages: [...prev[activeChatId].messages, newAgentMessage]
      }
    }));

    try {
      const url = new URL(`${API_BASE}/chat/stream`);
      url.searchParams.append('message', input);
      url.searchParams.append('agent_id', targetAgentId);

      const eventSource = new EventSource(url.toString());
      eventSourceRef.current = eventSource;

      let fullContent = '';

      eventSource.onmessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'intermediate') {
          fullContent += data.content;
          setChats(prev => ({
            ...prev,
            [activeChatId]: {
              ...prev[activeChatId],
              messages: prev[activeChatId].messages.map(msg => 
                msg.id === agentMessageId ? { ...msg, content: fullContent } : msg
              )
            }
          }));
        } else if (data.type === 'final') {
          setChats(prev => ({
            ...prev,
            [activeChatId]: {
              ...prev[activeChatId],
              isTyping: false,
              messages: prev[activeChatId].messages.map(msg => 
                msg.id === agentMessageId ? { ...msg, content: data.content, status: 'done' } : msg
              )
            }
          }));
          eventSource.close();
        } else if (data.type === 'error') {
          setChats(prev => ({
            ...prev,
            [activeChatId]: {
              ...prev[activeChatId],
              isTyping: false,
              messages: prev[activeChatId].messages.map(msg => 
                msg.id === agentMessageId ? { ...msg, content: "Error: " + data.content, status: 'error' } : msg
              )
            }
          }));
          eventSource.close();
        }
      };

      eventSource.onerror = (err) => {
        console.error("SSE Error:", err);
        setChats(prev => ({
          ...prev,
          [activeChatId]: { ...prev[activeChatId], isTyping: false }
        }));
        eventSource.close();
      };

    } catch (error) {
      console.error("Failed to connect to chat:", error);
      setChats(prev => ({
        ...prev,
        [activeChatId]: { ...prev[activeChatId], isTyping: false }
      }));
    }
  };

  const handleDMSelect = (agent: Agent) => {
    const id = `dm-${agent.name.toLowerCase()}`;
    if (!chats[id]) {
      setChats(prev => ({
        ...prev,
        [id]: {
          id,
          type: 'dm',
          name: agent.name,
          icon: '👤',
          messages: [
            {
              id: `dm-init-${agent.name}`,
              type: 'agent',
              speaker: agent.name,
              role: AGENT_ROLE_MAP[agent.name.toLowerCase()] || 'Agent',
              content: `Don Jimmy, I am at your disposal for direct tactical matters.`,
              timestamp: new Date(),
              status: 'done',
              avatar: AGENT_IMAGE_MAP[agent.name.toLowerCase()]
            }
          ],
          isTyping: false,
          agent_id: agent.name.toLowerCase()
        }
      }));
    }
    setActiveChatId(id);
  };

  const renderChannelButton = (ch: ChannelDef) => {
    const isSelected = activeChatId === ch.id;
    return (
      <button
        key={ch.id}
        onClick={() => setActiveChatId(ch.id)}
        title={ch.description}
        className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg transition-all group ${
          isSelected
            ? 'bg-surface-container-high text-on-surface'
            : 'text-outline hover:text-on-surface hover:bg-white/5'
        }`}
      >
        <span className={`text-base transition-opacity ${isSelected ? 'opacity-100' : 'opacity-50 group-hover:opacity-80'}`}>{ch.icon}</span>
        <span className={`font-body text-sm truncate ${ isSelected ? 'font-semibold text-on-surface' : 'font-medium'}`}>#{ch.label}</span>
        {isSelected && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />}
      </button>
    );
  };

  return (
    <div className="h-[calc(100vh-160px)] flex gap-6 overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Sub-Sidebar */}
      <aside className="w-64 flex flex-col gap-0 overflow-y-auto custom-scrollbar border border-outline/10 rounded-[22px] bg-surface-container-lowest/60 backdrop-blur-xl p-4">
        {/* Workspace Header */}
        <div className="flex items-center gap-2 px-1 py-3 mb-3 border-b border-outline/10">
          <div className="w-7 h-7 rounded-lg bg-primary/20 flex items-center justify-center text-sm border border-primary/30">🏛️</div>
          <div className="min-w-0">
            <p className="font-body text-xs font-bold text-on-surface truncate">La Passione Inc.</p>
            <p className="font-label text-[9px] uppercase tracking-widest text-outline">Famiglia Workspace</p>
          </div>
        </div>

        {/* Starred */}
        <div className="mb-4">
          <button className="w-full flex items-center gap-1.5 px-1 py-1.5 text-outline hover:text-on-surface group mb-1">
            <span className="material-symbols-outlined text-[14px]">star</span>
            <span className="font-label text-[10px] uppercase tracking-[0.25em]">Starred</span>
          </button>
          <div className="space-y-0.5">
            {STARRED_CHANNELS.map(renderChannelButton)}
          </div>
        </div>

        {/* All Channels */}
        <div className="mb-4">
          <button className="w-full flex items-center gap-1.5 px-1 py-1.5 text-outline hover:text-on-surface group mb-1">
            <span className="material-symbols-outlined text-[14px]">tag</span>
            <span className="font-label text-[10px] uppercase tracking-[0.25em]">Channels</span>
          </button>
          <div className="space-y-0.5">
            {ALL_CHANNELS.map(renderChannelButton)}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar pr-2">
          <h3 className="font-label text-[10px] uppercase tracking-[0.3em] text-outline mb-4 px-2">Direct Messages</h3>
          <div className="space-y-1">
            {agents.map(agent => {
              const id = `dm-${agent.name.toLowerCase()}`;
              const isSelected = activeChatId === id;
              return (
                <button
                  key={agent.name}
                  onClick={() => handleDMSelect(agent)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all group ${
                    isSelected 
                      ? 'bg-surface-container-high text-primary' 
                      : 'text-outline hover:text-on-surface hover:bg-white/5'
                  }`}
                >
                  <div className="relative">
                    <img 
                      src={AGENT_IMAGE_MAP[agent.name.toLowerCase()]} 
                      alt={agent.name}
                      className={`w-8 h-8 rounded-full object-cover border-2 transition-all ${isSelected ? 'border-primary shadow-[0_0_10px_rgba(255,179,181,0.3)]' : 'border-outline/20'}`}
                    />
                    <div className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-background ${
                      agent.status === 'thinking' ? 'bg-amber-500 animate-pulse' : 
                      agent.status === 'idle' ? 'bg-green-500' : 'bg-outline'
                    }`}></div>
                  </div>
                  <div className="flex flex-col items-start min-w-0">
                    <span className="font-body text-xs font-semibold truncate w-full">{agent.name}</span>
                    <span className="font-label text-[9px] uppercase tracking-tighter opacity-50 truncate w-full">
                      {AGENT_ROLE_MAP[agent.name.toLowerCase()] || 'Agent'}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 glass-module border border-outline/10 rounded-[28px] overflow-hidden flex flex-col bg-surface-container-lowest/40 shadow-2xl relative">
        {/* Chat Header */}
        <header className="px-8 py-5 border-b border-outline/5 flex items-center justify-between bg-surface-container-high/30 backdrop-blur-md z-10">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-2xl bg-primary/10 flex items-center justify-center text-xl border border-primary/20 shadow-inner">
              {activeChat.icon}
            </div>
            <div>
              <h2 className="font-headline text-lg text-white font-bold tracking-tight flex items-center gap-2">
                {activeChat.type === 'channel' ? `#${activeChat.name}` : activeChat.name}
              </h2>
              <p className="text-[10px] uppercase font-label tracking-widest text-outline-variant">
                {activeChat.type === 'channel' ? 'Public Channel' : activeChat.name + ' (Direct Message)'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
             <button className="w-9 h-9 rounded-full hover:bg-white/5 flex items-center justify-center transition-colors text-outline">
               <span className="material-symbols-outlined text-[20px]">info</span>
             </button>
             <button className="w-9 h-9 rounded-full hover:bg-white/5 flex items-center justify-center transition-colors text-outline">
               <span className="material-symbols-outlined text-[20px]">more_vert</span>
             </button>
          </div>
        </header>

        {/* Messages Feed */}
        <div className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar bg-gradient-to-b from-transparent to-black/10">
          <AnimatePresence initial={false}>
            {activeChat.messages.map((msg, idx) => {
              const isUser = msg.type === 'user';
              const showAvatar = idx === 0 || activeChat.messages[idx - 1].speaker !== msg.speaker;
              
              return (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  key={msg.id}
                  className={`flex gap-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
                >
                  {/* Avatar */}
                  <div className={`w-10 flex-shrink-0 flex flex-col items-center ${!showAvatar ? 'invisible' : ''}`}>
                    <img 
                      src={msg.avatar} 
                      className={`w-10 h-10 rounded-2xl border ${isUser ? 'border-primary/40' : 'border-outline/20'}`}
                      alt={msg.speaker}
                    />
                  </div>

                  {/* Bubble */}
                  <div className={`max-w-[70%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
                    {showAvatar && (
                      <div className={`flex items-center gap-2 mb-1 px-1 ${isUser ? 'flex-row-reverse' : ''}`}>
                        <span className={`font-body text-xs font-bold ${isUser ? 'text-primary' : 'text-on-surface'}`}>
                          {msg.speaker}
                        </span>
                        <span className="font-label text-[9px] uppercase tracking-tighter text-outline-variant">
                          {msg.role} • {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    )}
                    <div 
                      className={`px-5 py-3.5 rounded-[22px] text-sm leading-relaxed shadow-xl border ${
                        isUser 
                          ? 'bg-gradient-to-br from-[#6366f1] to-[#a855f7] text-white border-white/10 rounded-tr-none' 
                          : 'bg-surface-container-high/90 text-on-surface border-outline/5 rounded-tl-none backdrop-blur-sm'
                      }`}
                    >
                      {msg.content || (
                        <div className="flex gap-1.5 py-1">
                          <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0 }} className="w-1.5 h-1.5 rounded-full bg-primary"></motion.div>
                          <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.2 }} className="w-1.5 h-1.5 rounded-full bg-primary"></motion.div>
                          <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.4 }} className="w-1.5 h-1.5 rounded-full bg-primary"></motion.div>
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <footer className="p-6 bg-surface-container/50 border-t border-outline/10 backdrop-blur-xl">
           <div className="relative group bg-background/40 border border-outline/20 rounded-[24px] focus-within:border-primary/50 transition-all p-2 flex flex-col">
              <textarea 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
                placeholder={`Message ${activeChat.type === 'channel' ? '#' + activeChat.name : activeChat.name}...`}
                className="w-full bg-transparent border-none focus:ring-0 text-sm p-3 resize-none custom-scrollbar min-h-[48px] max-h-[200px]"
                rows={1}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = target.scrollHeight + 'px';
                }}
              />
              <div className="flex items-center justify-between px-2 pb-2">
                 <div className="flex items-center gap-1">
                    <button className="p-2 text-outline hover:text-white transition-colors"><span className="material-symbols-outlined text-[20px]">mood</span></button>
                    <button className="p-2 text-outline hover:text-white transition-colors"><span className="material-symbols-outlined text-[20px]">alternate_email</span></button>
                    <button className="p-2 text-outline hover:text-white transition-colors"><span className="material-symbols-outlined text-[20px]">attach_file</span></button>
                    <div className="w-[1px] h-4 bg-outline/20 mx-1"></div>
                    <button className="p-2 text-outline hover:text-white transition-colors"><span className="material-symbols-outlined text-[20px]">format_bold</span></button>
                    <button className="p-2 text-outline hover:text-white transition-colors"><span className="material-symbols-outlined text-[20px]">format_italic</span></button>
                 </div>
                 <button 
                  disabled={!input.trim() || activeChat.isTyping}
                  onClick={handleSend}
                  className={`p-2.5 rounded-xl transition-all flex items-center gap-2 ${
                    input.trim() && !activeChat.isTyping 
                      ? 'bg-gradient-to-r from-[#6366f1] to-[#a855f7] text-white shadow-lg shadow-indigo-500/20 hover:scale-105 active:scale-95' 
                      : 'bg-white/5 text-outline cursor-not-allowed opacity-50'
                  }`}
                 >
                   {activeChat.isTyping ? <span className="material-symbols-outlined text-[18px] animate-spin">refresh</span> : <span className="material-symbols-outlined text-[18px]">send</span>}
                   <span className="text-[10px] font-bold uppercase tracking-widest pr-1">Directive</span>
                 </button>
              </div>
           </div>
           <div className="mt-4 flex items-center justify-between px-2 opacity-40">
              <div className="flex items-center gap-4">
                 <span className="text-[9px] uppercase tracking-widest text-outline">Inter Font Active</span>
                 <span className="text-[9px] uppercase tracking-widest text-outline">SSE Stream Ready</span>
              </div>
              <span className="text-[9px] uppercase tracking-widest text-outline italic">Faithful to the Don's vision.</span>
           </div>
        </footer>
      </main>
    </div>
  );
}

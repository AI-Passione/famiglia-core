import React, { createContext, useContext, useState, useRef, useEffect, type ReactNode } from 'react';
import type { FamigliaAgent, Agent, ActionLog } from '../types';
import { API_BASE, BACKEND_BASE } from '../config';

// --- Shared Constants & Types ---

export interface Message {
  id: string;
  type: 'user' | 'agent';
  speaker: string;
  role: string;
  content: string;
  timestamp: Date;
  status?: 'sending' | 'typing' | 'done' | 'error';
  avatar?: string;
}

export interface ChatState {
  id: string;
  type: 'channel' | 'dm';
  name: string;
  icon: string;
  messages: Message[];
  isTyping: boolean;
  agent_id?: string;
  summary?: string; 
}

interface TerminalContextType {
  activeChatId: string;
  setActiveChatId: (id: string) => void;
  chats: Record<string, ChatState>;
  setChats: React.Dispatch<React.SetStateAction<Record<string, ChatState>>>;
  input: string;
  setInput: (val: string) => void;
  sendMessage: (text: string) => void;
  isTyping: boolean;
}

const TerminalContext = createContext<TerminalContextType | undefined>(undefined);

// Agent mappings (Shared)
export const AGENT_IMAGE_MAP: Record<string, string> = {
  alfredo: `${BACKEND_BASE}/api/v1/images/alfredo.png`,
  riccardo: `${BACKEND_BASE}/api/v1/images/riccardo.png`,
  vito: `${BACKEND_BASE}/api/v1/images/vito.png`,
  rossini: `${BACKEND_BASE}/api/v1/images/dr_rossini.png`,
  bella: `${BACKEND_BASE}/api/v1/images/bella.png`,
  tommy: `${BACKEND_BASE}/api/v1/images/tommy.png`,
  kowalski: `${BACKEND_BASE}/api/v1/images/kowalski.png`,
  giuseppina: `${BACKEND_BASE}/api/v1/images/giuseppina.png`,
};

export const AGENT_ROLE_MAP: Record<string, string> = {
  alfredo: 'The Orchestrator',
  riccardo: 'Master of Tech & Chaos',
  vito: 'Fiscal Guardian',
  rossini: 'Head of Intel & Product',
  bella: 'Mistress of Order',
  tommy: 'Logistics Runner',
  kowalski: 'Systems Scout',
  giuseppina: 'PR & Brand Excellence',
};

export const PRIO_CHANNELS = [
  { id: 'alerts', label: 'alerts', icon: '🚨', description: 'System alerts & critical signals', agent_id: 'riccardo', agentSpeaker: 'Riccardo', welcome: 'Don Jimmy, technical signals are within expected bands. I am monitoring for any anomaly.' },
  { id: 'incidents', label: 'incidents', icon: '🔥', description: 'Major technical incidents & resolution', agent_id: 'riccardo', agentSpeaker: 'Riccardo', welcome: 'Don Jimmy, #incidents is clear. Standing by for immediate stabilization.' },
];

export const BUSINESS_CHANNELS = [
  { id: 'command-center', label: 'command-center', icon: '🎯', description: 'Alfredo\'s orchestration hub', agent_id: 'alfredo', agentSpeaker: 'Alfredo', welcome: 'Don Jimmy, #command-center is secure. Awaiting your directives.' },
  { id: 'admin', label: 'admin', icon: '💋', description: 'Admin ops, scheduling & docs', agent_id: 'bella', agentSpeaker: 'Bella', welcome: 'Don Jimmy, your schedule and documents are pristine. How may I assist?' },
  { id: 'product', label: 'product', icon: '🔬', description: 'Product strategy & market research', agent_id: 'rossini', agentSpeaker: 'Dr. Rossini', welcome: 'Don Jimmy, the product roadmap is evolving nicely. What requires attention?' },
  { id: 'tech', label: 'tech', icon: '🔧', description: 'Code reviews, DevOps & engineering', agent_id: 'riccardo', agentSpeaker: 'Riccardo', welcome: 'Don Jimmy, the codebase is performant and secure. What needs to be built?' },
];

export const INTEL_CHANNELS = [
  { id: 'analytics', label: 'analytics', icon: '📊', description: 'Analytics, BI & data science', agent_id: 'kowalski', agentSpeaker: 'Kowalski', welcome: 'Don Jimmy, the metrics have been digested. What requirements do you have?' },
  { id: 'research-insights', label: 'research-insights', icon: '✨', description: 'Research insights & intelligence briefs', agent_id: 'rossini', agentSpeaker: 'Dr. Rossini', welcome: 'Don Jimmy, I have compiled fresh intelligence for the Famiglia.' },
];

export const OTHER_CHANNELS = [
  { id: 'agents-coordination', label: 'agents-coordination', icon: '🤝', description: 'Multi-agent workflow coordination', agent_id: 'alfredo', agentSpeaker: 'Alfredo', welcome: 'Don Jimmy, the agents are communicating and executing.' },
  { id: 'lounge', label: 'lounge', icon: '🥃', description: 'Ambient chatter & off-the-record briefs', agent_id: 'alfredo', agentSpeaker: 'Alfredo', welcome: 'Don Jimmy, the lounge is quiet tonight. Care for a brief?' },
  { id: 'social', label: 'social', icon: '📢', description: 'PR, brand & social strategy', agent_id: 'giuseppina', agentSpeaker: 'Giuseppina', welcome: 'Don Jimmy, the brand is immaculate. Shall we engage?' },
];

function buildInitialChats(): Record<string, ChatState> {
  const result: Record<string, ChatState> = {};
  [...PRIO_CHANNELS, ...BUSINESS_CHANNELS, ...INTEL_CHANNELS, ...OTHER_CHANNELS].forEach(ch => {
    result[ch.id] = {
      id: ch.id,
      type: 'channel',
      name: ch.label,
      icon: ch.icon,
      messages: [{
        id: `init-${ch.id}`,
        type: 'agent',
        speaker: ch.agentSpeaker || 'Agent',
        role: AGENT_ROLE_MAP[ch.agent_id?.toLowerCase() || ''] || 'Agent',
        content: ch.welcome,
        timestamp: new Date(),
        status: 'done',
        avatar: AGENT_IMAGE_MAP[ch.agent_id?.toLowerCase() || '']
      }],
      isTyping: false,
      agent_id: ch.agent_id,
      summary: "Mission operational. No critical deviations detected."
    };
  });
  return result;
}

export function TerminalProvider({ children }: { children: ReactNode }) {
  const [activeChatId, setActiveChatId] = useState<string>('command-center');
  const [chats, setChats] = useState<Record<string, ChatState>>(buildInitialChats());
  const [input, setInput] = useState('');
  const [agents, setAgents] = useState<FamigliaAgent[]>([]);
  const [actions, setActions] = useState<ActionLog[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Maintain REFS for high-frequency async operations (One Mind stability)
  const chatsRef = useRef(chats);
  const activeChatIdRef = useRef(activeChatId);

  useEffect(() => { chatsRef.current = chats; }, [chats]);
  useEffect(() => { activeChatIdRef.current = activeChatId; }, [activeChatId]);

  const activeChat = chats[activeChatId];

  // Fetch initial data (Agents & Actions)
  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log("[TerminalContext] Syncing agents & actions...");
        const [agentsRes, actionsRes] = await Promise.all([
          fetch(`${API_BASE}/agents`),
          fetch(`${API_BASE}/actions?limit=24`)
        ]);
        if (agentsRes.ok) {
           const agentsData = await agentsRes.json();
           setAgents(agentsData);
        }
        if (actionsRes.ok) {
           const data = await actionsRes.json();
           setActions(data.actions || []);
        }
      } catch (error) {
        console.error('[TerminalContext] Sync failure:', error);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Fetch history (Rehydration)
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        console.log("[TerminalContext] Rehydrating mission history...");
        const res = await fetch(`${API_BASE}/chat/conversations?limit=50`);
        if (res.ok) {
          // const conversations = await res.json();
          // Map backend conversations to chats if needed
          // For now, we continue using the provisioned channels but we could load thread history here
        }
      } catch (err) {
        console.error("[TerminalContext] History rehydration failed.", err);
      }
    };
    fetchHistory();
  }, []);

  // Sync ambient lounge messages
  useEffect(() => {
    if (activeChatId === 'lounge' && agents.length > 0) {
      const AMBIENT_LINES: Record<string, string> = {
        alfredo: 'The Famiglia is coordinated. Everything is moving with understated elegance.',
        riccardo: 'Codebase is stable. Everything is performance-tuned.',
        bella: 'Schedules are pristine, Don Jimmy.',
        rossini: 'Intelligence briefs are ready for review.',
      };

      const ambientMessages: Message[] = agents
        .filter(a => AMBIENT_LINES[a.agent_id.toLowerCase()])
        .map(agent => ({
          id: `ambient-${agent.agent_id}`,
          type: 'agent',
          speaker: agent.name,
          role: agent.role,
          content: AMBIENT_LINES[agent.agent_id.toLowerCase()],
          timestamp: new Date(),
          status: 'done',
          avatar: AGENT_IMAGE_MAP[agent.agent_id.toLowerCase()]
        }));
      setChats(prev => ({
        ...prev,
        'lounge': { ...prev['lounge'], messages: ambientMessages }
      }));
    }
  }, [agents, activeChatId]);

  // Sync actions channel
  useEffect(() => {
    if (activeChatId === 'agents-coordination' && actions.length > 0) {
      const opMessages: Message[] = actions.slice(0, 20).map(action => ({
        id: `op-${action.id}`,
        type: 'agent',
        speaker: action.agent_name,
        role: AGENT_ROLE_MAP[action.agent_name.toLowerCase()] || 'Agent',
        content: `Ack: ${action.action_type}. Status: ${action.approval_status || 'Executing'}`,
        timestamp: new Date(action.timestamp),
        status: 'done',
        avatar: AGENT_IMAGE_MAP[action.agent_name.toLowerCase()]
      }));
      setChats(prev => ({
        ...prev,
        'agents-coordination': { ...prev['agents-coordination'], messages: opMessages }
      }));
    }
  }, [actions, activeChatId]);

  useEffect(() => {
    return () => eventSourceRef.current?.close();
  }, []);

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    // USE REFS for mission-critical logic to avoid stale closures
    const currentChatId = activeChatIdRef.current;
    const currentChat = chatsRef.current[currentChatId];

    console.log(`[LA_PASSIONE_SYNC_v4] sendMessage triggered for channel [${currentChatId}]: "${text.slice(0, 20)}..."`);
    
    if (!currentChat) {
      console.warn("[TerminalContext] No chat state found for ID:", currentChatId);
      return;
    }

    if (currentChat.isTyping) {
      console.warn("[TerminalContext] Chat is busy, ignoring.");
      return;
    }

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      speaker: 'Don Jimmy',
      role: 'Head of Family',
      content: text,
      timestamp: new Date(),
      status: 'done'
    };

    // 1. Add user message
    setChats(prev => ({
      ...prev,
      [currentChatId]: {
        ...prev[currentChatId],
        messages: [...prev[currentChatId].messages, userMessage]
      }
    }));
    
    setInput('');

    // 2. Resolve target agent
    const targetAgentIdCandidate = currentChat.agent_id || (currentChatId === 'command-center' ? 'alfredo' : 'alfredo');
    const targetAgentId = targetAgentIdCandidate.toLowerCase();

    // 3. Add typing indicator (agent message placeholder)
    const agentMessageId = `agent-${Date.now()}`;
    const newAgentMessage: Message = {
      id: agentMessageId,
      type: 'agent',
      speaker: targetAgentId.charAt(0).toUpperCase() + targetAgentId.slice(1),
      role: AGENT_ROLE_MAP[targetAgentId] || 'Agent',
      content: '',
      timestamp: new Date(),
      status: 'typing',
      avatar: AGENT_IMAGE_MAP[targetAgentId]
    };
    
    setChats(prev => ({
      ...prev,
      [currentChatId]: {
        ...prev[currentChatId],
        isTyping: true,
        messages: [...prev[currentChatId].messages, newAgentMessage]
      }
    }));

    try {
      const url = new URL(`${API_BASE}/chat/stream`);
      url.searchParams.append('message', text);
      url.searchParams.append('agent_id', targetAgentId);
      url.searchParams.append('thread_id', currentChatId); // Use channel ID as thread
      
      console.log("[TerminalContext] 🚀 Connection initialized:", url.toString());

      const eventSource = new EventSource(url.toString());
      eventSourceRef.current = eventSource;

      let fullContent = '';

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'intermediate') {
            fullContent += data.content;
            setChats(prev => {
              const chat = prev[currentChatId];
              if (!chat) return prev;
              return {
                ...prev,
                [currentChatId]: {
                  ...chat,
                  messages: chat.messages.map(m => 
                    m.id === agentMessageId ? { ...m, content: fullContent } : m
                  )
                }
              };
            });
          } else if (data.type === 'final') {
            console.log(`[TerminalContext] ✅ Directive complete for ${currentChatId}`);
            setChats(prev => {
              const chat = prev[currentChatId];
              if (!chat) return prev;
              const finalContent = data.content;
              const summary = finalContent.length > 30 ? finalContent.slice(0, 100) + "..." : finalContent;
              
              return {
                ...prev,
                [currentChatId]: {
                  ...chat,
                  isTyping: false,
                  summary,
                  messages: chat.messages.map(m => 
                    m.id === agentMessageId ? { ...m, content: finalContent, status: 'done' } : m
                  )
                }
              };
            });
            eventSource.close();
          } else if (data.type === 'error') {
            console.error("[TerminalContext] Backend Error:", data.content);
            setChats(prev => {
              const chat = prev[currentChatId];
              if (!chat) return prev;
              return {
                ...prev,
                [currentChatId]: {
                  ...chat,
                  isTyping: false,
                  messages: chat.messages.map(m => 
                    m.id === agentMessageId ? { ...m, content: `Error: ${data.content}`, status: 'error' } : m
                  )
                }
              };
            });
            eventSource.close();
          }
        } catch (e) {
          console.error("[TerminalContext] SSE Parse error:", e);
        }
      };

      eventSource.onerror = (err) => {
        console.error("[TerminalContext] SSE Network Error:", err);
        setChats(prev => ({
          ...prev,
          [currentChatId]: { ...prev[currentChatId], isTyping: false }
        }));
        eventSource.close();
      };

    } catch (error) {
      console.error("[TerminalContext] Critical failure starting SSE:", error);
      setChats(prev => ({
        ...prev,
        [currentChatId]: { ...prev[currentChatId], isTyping: false }
      }));
    }
  };

  return (
    <TerminalContext.Provider value={{
      activeChatId,
      setActiveChatId,
      chats,
      setChats,
      input,
      setInput,
      sendMessage,
      isTyping: activeChat?.isTyping || false
    }}>
      {children}
    </TerminalContext.Provider>
  );
}

export const useTerminal = () => {
  const context = useContext(TerminalContext);
  if (!context) throw new Error('useTerminal must be used within a TerminalProvider');
  return context;
};

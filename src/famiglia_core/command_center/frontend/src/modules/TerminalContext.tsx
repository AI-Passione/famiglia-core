import React, { createContext, useContext, useState, useRef, useEffect, type ReactNode } from 'react';
import type { FamigliaAgent, ActionLog } from '../types';
import { API_BASE, BACKEND_BASE } from '../config';
import { useNotifications } from './NotificationContext';

// --- Shared Constants & Types ---

export interface Message {
  id: string;
  db_id?: number; // Backend DB ID for threading
  type: 'user' | 'agent';
  speaker: string;
  role: string;
  content: string;
  timestamp: Date;
  status?: 'sending' | 'typing' | 'done' | 'error';
  avatar?: string;
  parent_id?: number;
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
  activeThreadId: number | null;
  openThread: (messageDbId: number) => void;
  closeThread: () => void;
  chats: Record<string, ChatState>;
  setChats: React.Dispatch<React.SetStateAction<Record<string, ChatState>>>;
  input: string;
  setInput: (val: string) => void;
  sendMessage: (text: string, parentId?: number) => void;
  isTyping: boolean;
  isTerminalOpen: boolean;
  setTerminalOpen: (open: boolean) => void;
  addExternalAgentMessage: (content: string, agentId: string, chatId?: string) => void;
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
  { id: 'intelligence-hub', label: 'intelligence-hub', icon: '🧠', description: 'Intel & Strategy Co-op', agent_id: 'rossini', agentSpeaker: 'Dr. Rossini', welcome: 'Don Jimmy, the Intelligence Hub is online. Topics will route to myself, Riccardo, or Kowalski accordingly.' },
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
        role: AGENT_ROLE_MAP[String(ch.agent_id || '').toLowerCase()] || 'Agent',
        content: ch.welcome,
        timestamp: new Date(),
        status: 'done',
        avatar: AGENT_IMAGE_MAP[String(ch.agent_id || '').toLowerCase()]
      }],
      isTyping: false,
      agent_id: ch.agent_id,
      summary: "Mission operational. No critical deviations detected."
    };
  });
  return result;
}

export function TerminalProvider({ children, initialChatId = 'command-center' }: { children: ReactNode, initialChatId?: string }) {
  // Persistence: Restore last selected channel
  const [activeChatId, setActiveChatIdState] = useState<string>(() => {
    return localStorage.getItem('last_active_chat') || initialChatId;
  });
  const [activeThreadId, setActiveThreadId] = useState<number | null>(null);

  const setActiveChatId = (id: string) => {
    setActiveChatIdState(id);
    localStorage.setItem('last_active_chat', id);
  };

  const openThread = async (dbId: number) => {
    setActiveThreadId(dbId);
    // Optional: Fetch thread history if not already present or to ensure sync
    try {
      const res = await fetch(`${API_BASE}/chat/thread?parent_id=${dbId}`);
      if (res.ok) {
        const history = await res.json();
        const threadMessages = history.filter(Boolean).map((msg: any, idx: number) => {
          const senderLower = (msg.sender || "").toLowerCase();
          const isUser = msg.role === 'user' || senderLower.includes('don jimmy') || senderLower.includes('web_user');
          const targetSpeaker = isUser ? 'Don Jimmy' : (msg.sender || 'Agent');
          const targetRole = isUser ? 'Head of Family' : (msg.role || 'Agent');
          const mappingKey = String(targetSpeaker || 'Agent').split('(')[0].trim().toLowerCase();
          const targetAvatar = isUser ? undefined : AGENT_IMAGE_MAP[mappingKey] || AGENT_IMAGE_MAP['alfredo'];

          return {
            id: `thread-${dbId}-${idx}-${Date.now()}`,
            db_id: msg.id,
            type: isUser ? 'user' : 'agent',
            speaker: targetSpeaker,
            role: targetRole,
            content: msg.content,
            timestamp: new Date(msg.created_at || Date.now()),
            status: 'done',
            avatar: targetAvatar,
            parent_id: dbId
          };
        });

        setChats(prev => {
          const next = { ...prev };
          const chat = next[activeChatIdRef.current];
          if (chat) {
            // Merge thread messages ensuring no duplicates
            const existingIds = new Set(chat.messages.map(m => m.db_id));
            const newMessages = threadMessages.filter((m: any) => !existingIds.has(m.db_id));
            chat.messages = [...chat.messages, ...newMessages].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
          }
          return next;
        });
      }
    } catch (e) {
      console.error("[TerminalContext] Failed fetching thread history:", e);
    }
  };
  const closeThread = () => setActiveThreadId(null);

  const [chats, setChats] = useState<Record<string, ChatState>>(buildInitialChats());
  const [input, setInput] = useState('');
  const [isTerminalOpen, setTerminalOpen] = useState(false);
  const [agents, setAgents] = useState<FamigliaAgent[]>([]);
  const [actions, setActions] = useState<ActionLog[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Maintain REFS for high-frequency async operations (One Mind stability)
  const chatsRef = useRef(chats);
  const activeChatIdRef = useRef(activeChatId);

  useEffect(() => { chatsRef.current = chats; }, [chats]);
  useEffect(() => { activeChatIdRef.current = activeChatId; }, [activeChatId]);

  const activeChat = chats[activeChatId];

  const { addNotification } = useNotifications();
  const processedIdsRef = useRef<Set<number>>(new Set());
  const notifiedIdsRef = useRef<Set<number>>(new Set());

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
           setAgents(Array.isArray(agentsData) ? agentsData.filter(Boolean) : []);
        }
        if (actionsRes.ok) {
           const data = await actionsRes.json();
           setActions(Array.isArray(data.actions) ? data.actions.filter(Boolean) : []);
        }
      } catch (error) {
        console.error('[TerminalContext] Sync failure:', error);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Live polling for new messages (Real-time sync for background completion)
  useEffect(() => {
    const pollMessages = async () => {
      const currentChatId = activeChatIdRef.current;
      if (!currentChatId) return;

      // Special handling for lounge/coordination? 
      // Actually, we WANT to poll them for dialogue updates too.

      try {
        const res = await fetch(`${API_BASE}/chat/history?thread_id=${currentChatId}&limit=10`);
        if (res.ok) {
          const history = await res.json();
          if (!history || history.length === 0) return;

          const newMessagesFromBackend: any[] = [];
          
          history.forEach((msg: any) => {
            const backendId = Number(msg.id);
            if (!backendId) return;

            // 1. CHAT MESSAGE SYNC
            if (!processedIdsRef.current.has(backendId)) {
              processedIdsRef.current.add(backendId);
              
              const senderLower = String(msg.sender || "").toLowerCase();
              const isUser = msg.role === 'user' || senderLower.includes('don jimmy') || senderLower.includes('web_user');
              
              if (!isUser) {
                const targetSpeaker = msg.sender || 'Agent';
                const mappingKey = String(targetSpeaker).split('(')[0].trim().toLowerCase();
                const targetAvatar = AGENT_IMAGE_MAP[mappingKey] || AGENT_IMAGE_MAP['alfredo'];

                const mapped: Message = {
                  id: `poll-${currentChatId}-${backendId}-${Date.now()}`,
                  db_id: backendId,
                  type: 'agent',
                  speaker: targetSpeaker,
                  role: msg.role || 'Agent',
                  content: msg.content,
                  timestamp: new Date(msg.created_at || Date.now()),
                  status: 'done',
                  avatar: targetAvatar,
                  parent_id: msg.parent_id
                };
                newMessagesFromBackend.push(mapped);
              }
            }

            // 2. MISSION ALERT TRIGGER (Isolated from Chat Sync)
            if (msg.metadata && !notifiedIdsRef.current.has(backendId)) {
               if (msg.metadata.type === 'mission_completion') {
                 notifiedIdsRef.current.add(backendId);
                 addNotification(
                   "Mission Accomplished",
                   msg.content.split('\n')[0],
                   msg.metadata.status === 'failed' ? 'error' : 'success',
                   msg.metadata.task_id
                 );
               } else if (msg.metadata.type === 'mission_dispatch') {
                 notifiedIdsRef.current.add(backendId);
                 addNotification(
                   "Mission Dispatched",
                   msg.content.split('\n')[0],
                   'info',
                   msg.metadata.task_id
                 );
               }
            }
          });

          if (newMessagesFromBackend.length > 0) {
            setChats(prev => {
              const chat = prev[currentChatId];
              if (!chat) return prev;
              
              // Only add messages that aren't already in the local state (by db_id)
              const existingDbIds = new Set(chat.messages.map(m => m.db_id).filter(Boolean));
              const uniqueNew = newMessagesFromBackend.filter(m => !existingDbIds.has(m.db_id));
              
              if (uniqueNew.length === 0) return prev;
              
              return {
                ...prev,
                [currentChatId]: {
                  ...chat,
                  messages: [...chat.messages, ...uniqueNew].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
                }
              };
            });
          }
        }
      } catch (e) {
        console.error("[TerminalContext] Polling failed:", e);
      }
    };

    const pollInterval = setInterval(pollMessages, 5000);
    return () => clearInterval(pollInterval);
  }, [addNotification]);

  // Global Notification Polling (Cross-channel signals)
  useEffect(() => {
    const pollGlobalNotifications = async () => {
      try {
        const res = await fetch(`${API_BASE}/chat/notifications?limit=20`);
        if (res.ok) {
          const notifications = await res.json();
          notifications.forEach((msg: any) => {
            const backendId = Number(msg.id);
            if (backendId && !notifiedIdsRef.current.has(backendId)) {
              notifiedIdsRef.current.add(backendId);

              // CHECK FOR COMPLETION NOTIFICATION
              if (msg.metadata && msg.metadata.type === 'mission_completion') {
                 addNotification(
                   "Mission Accomplished",
                   msg.content.split('\n')[0],
                   msg.metadata.status === 'failed' ? 'error' : 'success',
                   msg.metadata.task_id
                 );
              } else if (msg.metadata && msg.metadata.type === 'mission_dispatch') {
                addNotification(
                  "Mission Dispatched",
                  msg.content.split('\n')[0],
                  'info',
                  msg.metadata.task_id
                );
              }
            }
          });
        }
      } catch (e) {
        console.error("[TerminalContext] Global notification polling failed:", e);
      }
    };

    const interval = setInterval(pollGlobalNotifications, 10000); // Pulse every 10s
    return () => clearInterval(interval);
  }, [addNotification]);

  // Fetch history (Rehydration)
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        console.log("[TerminalContext] Rehydrating mission history...");
        const allChannels = [...PRIO_CHANNELS, ...BUSINESS_CHANNELS, ...INTEL_CHANNELS, ...OTHER_CHANNELS];
        const historyUpdates: Record<string, Message[]> = {};

        await Promise.all(allChannels.map(async (channel) => {
          try {
            const res = await fetch(`${API_BASE}/chat/history?thread_id=${channel.id}&limit=50`);
            if (res.ok) {
              const history = await res.json();
              if (history && history.length > 0) {
                // Map backend messages to frontend format
                const loadedMessages: Message[] = history.filter(Boolean).map((msg: any, idx: number) => {
                   try {
                     const backendId = Number(msg.id);
                     if (backendId) processedIdsRef.current.add(backendId);

                     const senderLower = String(msg.sender || "").toLowerCase();
                     const isUser = msg.role === 'user' || senderLower.includes('don jimmy') || senderLower.includes('web_user');
                     
                     const targetSpeaker = isUser ? 'Don Jimmy' : (msg.sender || channel.agentSpeaker || 'Agent');
                     const targetRole = isUser ? 'Head of Family' : (msg.role || 'Agent');
                     const mappingKey = String(targetSpeaker || "").split('(')[0].trim().toLowerCase();
                     const chAgentId = String(channel.agent_id || 'alfredo').toLowerCase();
                     const targetAvatar = isUser ? undefined : AGENT_IMAGE_MAP[mappingKey] || AGENT_IMAGE_MAP[chAgentId];

                      return {
                        id: `hist-${channel.id}-${idx}-${Date.now()}`,
                        db_id: backendId,
                        type: isUser ? 'user' : 'agent',
                        speaker: targetSpeaker,
                        role: targetRole,
                        content: msg.content,
                        timestamp: new Date(msg.created_at || Date.now()),
                        status: 'done',
                        avatar: targetAvatar,
                        parent_id: msg.parent_id
                      };
                   } catch (e) {
                     console.error("[TC_TRACK] Error in history rehydration map:", e, msg);
                     throw e;
                   }
                });
                historyUpdates[channel.id] = loadedMessages;
              }
            }
          } catch (e) {
            console.error(`[TerminalContext] Failed rehydrating ${channel.id}:`, e);
          }
        }));

        if (Object.keys(historyUpdates).length > 0) {
          setChats(prev => {
            const next = { ...prev };
            Object.entries(historyUpdates).forEach(([chid, messages]) => {
              if (next[chid]) {
                const initMsg = next[chid].messages[0];
                next[chid] = {
                  ...next[chid],
                  messages: [initMsg, ...messages]
                };
              }
            });
            return next;
          });
        }
      } catch (err) {
        console.error("[TerminalContext] History rehydration failed.", err);
      }
    };
    fetchHistory();
  }, []);

  // Sync ambient lounge messages
  useEffect(() => {
    try {
      if (activeChatId === 'lounge' && agents.length > 0) {
        const AMBIENT_LINES: Record<string, string> = {
          alfredo: 'The Famiglia is coordinated. Everything is moving with understated elegance.',
          riccardo: 'Codebase is stable. Everything is performance-tuned.',
          bella: 'Schedules are pristine, Don Jimmy.',
          rossini: 'Intelligence briefs are ready for review.',
        };

        const ambientMessages: Message[] = agents
          .filter(a => {
            console.log("[TC_TRACE] filter agents", a);
            try {
              return a && typeof a.agent_id === 'string' && AMBIENT_LINES[a.agent_id.toLowerCase()];
            } catch (e) {
              console.error("[TC_TRACK] Error in ambient filter:", e, a);
              return false;
            }
          })
          .map(agent => {
            try {
              return {
                id: `ambient-${agent.agent_id}-${Date.now()}`,
                type: 'agent',
                speaker: agent.name || 'Agent',
                role: agent.role || 'Agent',
                content: AMBIENT_LINES[agent.agent_id.toLowerCase()] || 'Silence in the lounge.',
                timestamp: new Date(),
                status: 'done',
                avatar: AGENT_IMAGE_MAP[agent.agent_id.toLowerCase()]
              };
            } catch (e) {
              console.error("[TC_TRACK] Error in ambient map:", e, agent);
              throw e;
            }
          });
        setChats(prev => {
          const base = prev['lounge'];
          if (!base) return prev;
          return {
            ...prev,
            'lounge': { ...base, messages: ambientMessages }
          };
        });
      }
    } catch (e) {
      console.error("[TerminalContext] Lounge sync crash:", e);
    }
  }, [agents, activeChatId]);

  // Sync actions channel (Operational Pulse)
  useEffect(() => {
    if (activeChatId === 'agents-coordination' && actions.length > 0) {
      const opMessages: Message[] = actions.slice(0, 20).map(action => {
        const agentKey = String(action.agent_name || 'agent').toLowerCase();
        return {
          id: `op-${action.id}`,
          type: 'agent',
          speaker: action.agent_name || 'Agent',
          role: AGENT_ROLE_MAP[agentKey] || 'Agent',
          content: `Ack: ${action.action_type || 'Action'}. Status: ${action.approval_status || 'Executing'}`,
          timestamp: new Date(action.timestamp),
          status: 'done',
          avatar: AGENT_IMAGE_MAP[agentKey]
        };
      });

      setChats(prev => {
        const base = prev['agents-coordination'];
        if (!base) return prev;

        // Merge Strategy:
        // 1. Keep all non-operational messages (dialogue, external, manual)
        // 2. Filter out old operational messages to refresh with new ones
        // 3. Combine and sort by timestamp
        const dialogueMessages = base.messages.filter(m => !m.id.startsWith('op-'));
        const combined = [...dialogueMessages, ...opMessages]
          .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

        // Deduplicate by content and timestamp to avoid flickering
        const seen = new Set();
        const dedupedByContent = combined.filter(m => {
          const key = `${m.speaker}:${m.content}:${m.timestamp.getTime()}`;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });

        return {
          ...prev,
          'agents-coordination': { ...base, messages: dedupedByContent }
        };
      });
    }
  }, [actions, activeChatId]);

  useEffect(() => {
    return () => eventSourceRef.current?.close();
  }, []);

  const sendMessage = async (text: string, parentId?: number) => {
    if (!text.trim()) return;

    // USE REFS for mission-critical logic to avoid stale closures
    const currentChatId = activeChatIdRef.current;
    const currentChat = chatsRef.current[currentChatId];

    console.log(`[LA_PASSIONE_SYNC_v4] sendMessage triggered [parent=${parentId}] for channel [${currentChatId}]: "${text.slice(0, 20)}..."`);
    
    if (!currentChat) {
      console.warn("[TerminalContext] No chat state found for ID:", currentChatId);
      return;
    }

    // Only block main channel inputs, threads can be concurrent maybe? 
    // For now, let's keep it simple and block if the specific "context" is typing.
    if (currentChat.isTyping && !parentId) {
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
      status: 'done',
      parent_id: parentId
    };

    // 1. Add user message
    setChats(prev => ({
      ...prev,
      [currentChatId]: {
        ...prev[currentChatId],
        messages: [...prev[currentChatId].messages, userMessage]
      }
    }));
    
    if (!parentId) setInput('');

    // 2. Resolve target agent
    let targetAgentIdCandidate = currentChat.agent_id || (currentChatId === 'command-center' ? 'alfredo' : 'alfredo');
    
    // Dynamic Topic Routing for Intelligence Hub
    if (currentChatId === 'intelligence-hub' && !parentId) {
      const lowerText = text.toLowerCase();
      if (lowerText.match(/\b(tech|code|system|devops|engineering|bug|deploy|architecture|app|repo|github)\b/)) {
        targetAgentIdCandidate = 'riccardo';
      } else if (lowerText.match(/\b(data|analytics|metrics|dashboard|sql|numbers|query|stats|duckdb)\b/)) {
        targetAgentIdCandidate = 'kowalski';
      } else {
        targetAgentIdCandidate = 'rossini';
      }
    }

    const targetAgentId = String(targetAgentIdCandidate || 'alfredo').toLowerCase();

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
      avatar: AGENT_IMAGE_MAP[targetAgentId],
      parent_id: parentId
    };
    
    setChats(prev => ({
      ...prev,
      [currentChatId]: {
        ...prev[currentChatId],
        isTyping: !parentId ? true : prev[currentChatId].isTyping,
        messages: [...prev[currentChatId].messages, newAgentMessage]
      }
    }));

    try {
      const url = new URL(`${API_BASE}/chat/stream`);
      url.searchParams.append('message', text);
      url.searchParams.append('agent_id', targetAgentId);
      url.searchParams.append('thread_id', currentChatId); // Use channel ID as thread
      if (parentId) url.searchParams.append('parent_id', parentId.toString());
      
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
  
  const addExternalAgentMessage = (content: string, agentId: string, chatId: string = 'command-center') => {
    const aid = agentId.toLowerCase();
    const msg: Message = {
      id: `ext-${Date.now()}`,
      type: 'agent',
      speaker: aid.charAt(0).toUpperCase() + aid.slice(1),
      role: AGENT_ROLE_MAP[aid] || 'Agent',
      content,
      timestamp: new Date(),
      status: 'done',
      avatar: AGENT_IMAGE_MAP[aid] || AGENT_IMAGE_MAP['alfredo']
    };
    
    setChats(prev => {
      const chat = prev[chatId];
      if (!chat) return prev;
      return {
        ...prev,
        [chatId]: {
          ...chat,
          messages: [...chat.messages, msg]
        }
      };
    });
  };

  return (
    <TerminalContext.Provider value={{
      activeChatId,
      setActiveChatId,
      activeThreadId,
      openThread,
      closeThread,
      chats,
      setChats,
      input,
      setInput,
      sendMessage,
      isTyping: activeChat?.isTyping || false,
      isTerminalOpen,
      setTerminalOpen,
      addExternalAgentMessage
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

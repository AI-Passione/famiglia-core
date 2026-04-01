import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_BASE } from '../../config';

interface Message {
  id: string;
  type: 'user' | 'agent';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'typing' | 'done' | 'error';
}

export function DirectivesTerminal() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'initial',
      type: 'agent',
      content: "Don Jimmy, I am at your disposal. What are your instructions?",
      timestamp: new Date(),
      status: 'done'
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    console.log("DirectivesTerminal mounted. isOpen:", isOpen);
  }, [isOpen]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date(),
      status: 'done'
    };

    setMessages((prev: Message[]) => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    const agentMessageId = (Date.now() + 1).toString();
    const newAgentMessage: Message = {
      id: agentMessageId,
      type: 'agent',
      content: '',
      timestamp: new Date(),
      status: 'typing'
    };
    
    setMessages((prev: Message[]) => [...prev, newAgentMessage]);

    try {
      const url = new URL(`${API_BASE}/chat/stream`);
      url.searchParams.append('message', input);
      url.searchParams.append('agent_id', 'alfredo');

      const eventSource = new EventSource(url.toString());
      eventSourceRef.current = eventSource;

      let fullContent = '';

      eventSource.onmessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'intermediate') {
          fullContent += data.content;
          setMessages((prev: Message[]) => prev.map((msg: Message) => 
            msg.id === agentMessageId ? { ...msg, content: fullContent } : msg
          ));
        } else if (data.type === 'final') {
          setMessages((prev: Message[]) => prev.map((msg: Message) => 
            msg.id === agentMessageId ? { ...msg, content: data.content, status: 'done' } : msg
          ));
          setIsTyping(false);
          eventSource.close();
        } else if (data.type === 'error') {
          setMessages((prev: Message[]) => prev.map((msg: Message) => 
            msg.id === agentMessageId ? { ...msg, content: "Error: " + data.content, status: 'error' } : msg
          ));
          setIsTyping(false);
          eventSource.close();
        }
      };

      eventSource.onerror = (err) => {
        console.error("SSE Error:", err);
        setIsTyping(false);
        eventSource.close();
      };

    } catch (error) {
      console.error("Failed to connect to chat:", error);
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const target = e.target as HTMLTextAreaElement;
    target.style.height = 'auto';
    target.style.height = `${target.scrollHeight}px`;
  };

  return (
    <div className="fixed bottom-8 right-8 z-[60] flex flex-col items-end gap-4">
      <AnimatePresence mode="wait">
        {isOpen && (
          <motion.div
            key="directives-terminal-window"
            initial={{ opacity: 0, y: 20, scale: 0.95, width: '400px', height: '600px' }}
            animate={{ 
              opacity: 1, 
              y: 0, 
              scale: 1,
              width: isMaximized ? '80vw' : '400px',
              height: isMaximized ? '80vh' : '600px'
            }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="glass-module border border-outline/20 rounded-xl shadow-[0px_32px_64px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col mb-4 bg-surface/90 backdrop-blur-xl"
          >
            {/* Header */}
            <div className="px-5 py-4 border-b border-outline/10 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center border border-primary/30">
                  <span className="material-symbols-outlined text-primary text-sm">smart_toy</span>
                </div>
                <div>
                  <h3 className="font-headline text-sm uppercase tracking-widest text-on-surface">Directives Terminal</h3>
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div>
                    <span className="text-[10px] uppercase font-label tracking-tighter text-outline-variant">Agent Alfredo Online</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => setIsMaximized(!isMaximized)}
                  className="p-1.5 hover:bg-white/5 rounded-full transition-colors text-outline-variant hover:text-on-surface"
                >
                  {isMaximized ? <span className="material-symbols-outlined text-[16px]">close_fullscreen</span> : <span className="material-symbols-outlined text-[16px]">open_in_full</span>}
                </button>
                <button 
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 hover:bg-white/5 rounded-full transition-colors text-outline-variant hover:text-on-surface"
                >
                  <span className="material-symbols-outlined text-[16px]">close</span>
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6 custom-scrollbar bg-background/30">
              {messages.map((msg) => (
                <div 
                  key={msg.id} 
                  className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[85%] flex flex-col ${msg.type === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className={`px-4 py-3 rounded-2xl text-[13px] leading-relaxed shadow-sm ${
                      msg.type === 'user' 
                        ? 'bg-gradient-to-br from-[#6366f1] to-[#a855f7] text-white rounded-tr-none' 
                        : 'bg-surface-container-high/80 text-on-surface rounded-tl-none border border-outline/5'
                    }`}>
                      {msg.content}
                      {msg.status === 'typing' && msg.content === '' && (
                        <div className="flex gap-1 py-1">
                          <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0 }} className="w-1.5 h-1.5 rounded-full bg-primary"></motion.div>
                          <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.2 }} className="w-1.5 h-1.5 rounded-full bg-primary"></motion.div>
                          <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.4 }} className="w-1.5 h-1.5 rounded-full bg-primary"></motion.div>
                        </div>
                      )}
                    </div>
                    <span className="text-[9px] uppercase tracking-widest mt-1.5 text-outline-variant flex items-center gap-1 opacity-60">
                      {msg.type === 'user' ? 'Don Jimmy' : 'Alfredo'} • {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              ))}
              {isTyping && messages[messages.length - 1].status !== 'typing' && (
                <div className="flex justify-start">
                  <div className="bg-surface-container-high/80 px-4 py-3 rounded-2xl rounded-tl-none border border-outline/5 flex gap-1">
                    <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0 }} className="w-1.5 h-1.5 rounded-full bg-primary"></motion.div>
                    <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.2 }} className="w-1.5 h-1.5 rounded-full bg-primary"></motion.div>
                    <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.4 }} className="w-1.5 h-1.5 rounded-full bg-primary"></motion.div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 bg-surface-container/80 border-t border-outline/10 flex flex-col gap-2">
              <div className="relative flex items-end gap-2 bg-background/50 border border-outline/10 rounded-xl p-2 px-3 focus-within:border-primary/30 transition-all group">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Issue a directive..."
                  rows={1}
                  className="flex-1 bg-transparent border-none focus:ring-0 text-sm py-1.5 resize-none custom-scrollbar min-h-[36px] max-h-[120px] placeholder:text-outline-variant text-on-surface"
                  style={{ height: 'auto' }}
                  onInput={handleInput}
                />
                <div className="flex items-center gap-1.5 pb-1">
                  <button className="p-1.5 text-outline-variant hover:text-primary transition-colors rounded-lg hover:bg-primary/5">
                    <span className="material-symbols-outlined text-[18px]">attach_file</span>
                  </button>
                  <button 
                    disabled={!input.trim() || isTyping}
                    onClick={handleSend}
                    className={`p-2 rounded-lg transition-all ${
                      input.trim() && !isTyping
                        ? 'bg-primary text-on-primary shadow-[0_0_15px_rgba(255,179,181,0.3)]' 
                        : 'bg-white/5 text-outline-variant cursor-not-allowed'
                    }`}
                  >
                    {isTyping ? <span className="material-symbols-outlined text-[18px] animate-spin">refresh</span> : <span className="material-symbols-outlined text-[18px]">send</span>}
                  </button>
                </div>
              </div>
              <div className="flex items-center justify-between px-1">
                <span className="text-[9px] uppercase tracking-tighter text-outline-variant">Press Enter to send, Shift+Enter for new line</span>
                <span className="text-[9px] uppercase tracking-tighter text-outline-variant">Agent: Alfredo (Senior Butler)</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <button 
        onClick={() => {
          console.log("DirectivesTerminal toggle clicked. Current isOpen:", isOpen);
          setIsOpen(!isOpen);
        }}
        className="bg-[#4A0404] text-white rounded-full p-4 shadow-[0px_24px_48px_rgba(0,0,0,0.4)] border border-[#ffb3b5]/10 hover:scale-105 active:scale-95 transition-all duration-300 flex items-center gap-3 group relative overflow-hidden"
      >
        <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.4 }}
        >
          {isOpen ? <span className="material-symbols-outlined">close</span> : <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>chat</span>}
        </motion.div>
        {!isOpen && (
          <span className="font-label text-[10px] uppercase tracking-widest font-bold pr-2">Directives Terminal</span>
        )}
      </button>
    </div>
  );
}

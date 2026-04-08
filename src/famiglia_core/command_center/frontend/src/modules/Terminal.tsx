import { useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  useTerminal, 
  PRIO_CHANNELS, 
  BUSINESS_CHANNELS, 
  INTEL_CHANNELS, 
  OTHER_CHANNELS 
} from './TerminalContext';
import { ThreadPanel } from './ThreadPanel';

interface TerminalProps {
  variant?: 'full' | 'compact';
}

export function Terminal({ variant = 'full' }: TerminalProps) {
  const { 
    activeChatId, 
    setActiveChatId, 
    activeThreadId,
    openThread,
    chats, 
    input, 
    setInput, 
    sendMessage,
    isTyping 
  } = useTerminal();

  const scrollRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [hasNewMessages, setHasNewMessages] = useState(false);
  const lastMessageCount = useRef(0);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeChat = chats[activeChatId];
  const [showSummary, setShowSummary] = useState(variant === 'compact');

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const atBottom = scrollHeight - scrollTop - clientHeight < 50;
    setIsAtBottom(atBottom);
    if (atBottom) setHasNewMessages(false);
  };

  const scrollToBottom = (behavior: ScrollBehavior = "smooth") => {
    if (scrollRef.current) {
       scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior });
       setHasNewMessages(false);
    }
  };

  useEffect(() => {
    const currentCount = activeChat?.messages.length || 0;
    const lastMsg = activeChat?.messages[currentCount - 1];
    const isUserMsg = lastMsg?.type === 'user';

    if (currentCount > lastMessageCount.current) {
      if (isAtBottom || isUserMsg) {
        scrollToBottom(isUserMsg ? "auto" : "smooth");
      } else {
        setHasNewMessages(true);
      }
    }
    lastMessageCount.current = currentCount;
  }, [activeChat?.messages, isTyping]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const renderChannelButton = (ch: any) => {
    const isActive = activeChatId === ch.id;
    return (
      <button
        key={ch.id}
        onClick={() => setActiveChatId(ch.id)}
        className={`w-full flex items-center justify-between px-3 py-2 rounded-xl transition-all duration-300 group ${
          isActive 
            ? 'bg-primary/10 text-primary shadow-[inset_0_0_12px_rgba(255,179,181,0.05)]' 
            : 'text-outline hover:bg-white/5 hover:text-on-surface'
        }`}
      >
        <div className="flex items-center gap-3">
          <span className="text-lg opacity-70 group-hover:scale-110 transition-transform">{ch.icon}</span>
          <span className="font-label text-xs uppercase tracking-widest">{ch.label}</span>
        </div>
        {isActive && (
          <motion.div layoutId="active-pill" className="w-1 h-1 rounded-full bg-primary shadow-[0_0_8px_rgba(255,179,181,0.8)]" />
        )}
      </button>
    );
  };

  if (!activeChat) return <div className="p-10 text-center text-outline">Initializing secure connection...</div>;

  return (
    <div className={`flex bg-surface-container-lowest/10 backdrop-blur-md overflow-hidden ${variant === 'full' ? 'h-full' : 'h-[600px] w-full'}`}>
      {variant === 'full' && (
        <aside className="w-72 border-r border-outline/5 flex flex-col bg-surface-container-low/30">
          <div className="p-6 border-b border-outline/5">
            <h2 className="font-headline text-sm uppercase tracking-[0.3em] text-primary opacity-80 italic">Hierarchy</h2>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
            {/* Categories */}
            <div className="space-y-4">
              <div>
                <button className="w-full flex items-center gap-1.5 px-1 py-1.5 text-red-400 font-bold group mb-1">
                  <span className="material-symbols-outlined text-[14px]">priority_high</span>
                  <span className="font-label text-[10px] uppercase tracking-[0.25em]">PRIO</span>
                </button>
                <div className="space-y-0.5">{PRIO_CHANNELS.map(renderChannelButton)}</div>
              </div>

              <div>
                <button className="w-full flex items-center gap-1.5 px-1 py-1.5 text-outline hover:text-on-surface group mb-1">
                  <span className="material-symbols-outlined text-[14px]">business_center</span>
                  <span className="font-label text-[10px] uppercase tracking-[0.25em]">Business</span>
                </button>
                <div className="space-y-0.5">{BUSINESS_CHANNELS.map(renderChannelButton)}</div>
              </div>

              <div>
                <button className="w-full flex items-center gap-1.5 px-1 py-1.5 text-outline hover:text-on-surface group mb-1">
                  <span className="material-symbols-outlined text-[14px]">psychology</span>
                  <span className="font-label text-[10px] uppercase tracking-[0.25em]">Intel</span>
                </button>
                <div className="space-y-0.5">{INTEL_CHANNELS.map(renderChannelButton)}</div>
              </div>

              <div>
                <button className="w-full flex items-center gap-1.5 px-1 py-1.5 text-outline hover:text-on-surface group mb-1">
                  <span className="material-symbols-outlined text-[14px]">more_horiz</span>
                  <span className="font-label text-[10px] uppercase tracking-[0.25em]">Others</span>
                </button>
                <div className="space-y-0.5">{OTHER_CHANNELS.map(renderChannelButton)}</div>
              </div>
            </div>
          </div>
        </aside>
      )}

      <div className="flex-1 flex flex-row overflow-hidden relative">
        <main className="flex-1 flex flex-col bg-background/20 relative overflow-hidden">
        {/* Information Compression Layer (Summary Bar) */}
        <AnimatePresence>
          {showSummary && activeChat.summary && (
            <motion.div 
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="bg-primary/5 border-b border-primary/10 overflow-hidden"
            >
              <div className="p-3 px-5 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 flex-1">
                  <span className="material-symbols-outlined text-primary text-sm">summarize</span>
                  <p className="text-[11px] text-on-surface/80 italic line-clamp-1 leading-relaxed">
                    <span className="font-bold text-primary mr-2 uppercase tracking-tighter">SITREP:</span>
                    {activeChat.summary}
                  </p>
                </div>
                <button 
                  onClick={() => setShowSummary(false)}
                  className="text-outline hover:text-on-surface transition-colors"
                >
                  <span className="material-symbols-outlined text-sm">close</span>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Chat Header */}
        <header className="px-6 py-4 border-b border-outline/5 flex items-center justify-between bg-surface-container-lowest/40 backdrop-blur-md sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-2xl bg-primary/20 flex items-center justify-center border border-primary/30 shadow-[0_0_15px_rgba(255,179,181,0.1)]">
              <span className="text-xl">{activeChat.icon}</span>
            </div>
            <div>
              <h1 className="font-headline text-lg italic tracking-tight text-on-surface">#{activeChat.name}</h1>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]"></div>
                <span className="text-[10px] uppercase font-label tracking-widest text-outline">Channel Synchronized</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {!showSummary && activeChat.summary && (
              <button 
                onClick={() => setShowSummary(true)}
                className="p-2 hover:bg-primary/10 rounded-lg transition-all text-primary border border-primary/20 flex items-center gap-2"
              >
                <span className="material-symbols-outlined text-[16px]">bolt</span>
                <span className="text-[9px] font-bold uppercase tracking-widest">Compress</span>
              </button>
            )}
            <button className="p-2 hover:bg-white/5 rounded-lg transition-colors text-outline-variant hover:text-on-surface">
              <span className="material-symbols-outlined text-[20px]">search</span>
            </button>
            <button className="p-2 hover:bg-white/5 rounded-lg transition-colors text-outline-variant hover:text-on-surface">
              <span className="material-symbols-outlined text-[20px]">more_vert</span>
            </button>
          </div>
        </header>

        {/* Messages */}
        <div 
          ref={scrollRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar relative"
        >
          {activeChat.messages.filter(m => !m.parent_id).map((msg, i) => {
            const isUser = msg.type === 'user';
            return (
              <motion.div 
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className={`flex gap-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
              >
                {!isUser && (
                  <div className="flex-shrink-0 mt-1">
                    <div className="w-8 h-8 rounded-full border border-outline/10 p-0.5 bg-background overflow-hidden">
                      <img src={msg.avatar} alt="avatar" className="w-full h-full object-cover rounded-full grayscale hover:grayscale-0 transition-all duration-500" />
                    </div>
                  </div>
                )}
                <div className={`max-w-[70%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
                  <div className="flex items-center gap-2 mb-1.5 px-1">
                    <span className="text-[10px] font-headline uppercase tracking-widest text-[#a38b88]">{msg.speaker}</span>
                    <span className="text-[8px] uppercase tracking-tighter text-outline opacity-50">{msg.role} • {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                  <div className={`p-4 rounded-3xl text-[13px] leading-relaxed relative group transition-all duration-300 ${isUser 
                    ? 'bg-primary/10 text-on-surface rounded-tr-none border border-primary/20 shadow-[0_4px_20px_rgba(255,179,181,0.05)]' 
                    : 'bg-surface-container-high/40 text-on-surface rounded-tl-none border border-outline/5 hover:bg-surface-container-high/60 shadow-sm'
                  }`}>
                    {msg.content}
                    
                    {/* Thread Trigger */}
                    <button 
                      onClick={() => msg.db_id && openThread(msg.db_id)}
                      className="absolute top-2 right-2 p-1.5 bg-background/80 rounded-lg border border-outline/10 opacity-0 group-hover:opacity-100 transition-all hover:text-primary hover:border-primary/30 shadow-lg translate-x-2"
                    >
                      <span className="material-symbols-outlined text-[16px]">reply</span>
                    </button>

                    {msg.status === 'typing' && (
                      <div className="flex gap-1 py-1 mt-1">
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
          <div ref={messagesEndRef} />
        </div>

        {/* Jump to Bottom */}
        <AnimatePresence>
          {hasNewMessages && (
            <motion.button
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              onClick={() => scrollToBottom()}
              className="absolute bottom-32 left-1/2 -translate-x-1/2 px-4 py-2 bg-primary text-on-primary rounded-full shadow-2xl flex items-center gap-2 z-30 font-label text-[10px] uppercase tracking-widest"
            >
              <span className="material-symbols-outlined text-sm">arrow_downward</span>
              New Messages
            </motion.button>
          )}
        </AnimatePresence>

        {/* Input */}
        <footer className="p-6 pt-2 bg-surface-container-lowest/50 backdrop-blur-xl border-t border-outline/5">
          <div className="relative group">
            <div className="absolute inset-x-0 -top-px h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent opacity-0 group-focus-within:opacity-100 transition-opacity"></div>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder={`Compose directive for #${activeChat.name}...`}
              className="w-full bg-surface-container/30 border border-outline/10 rounded-2xl p-4 pr-32 focus:ring-0 focus:border-primary/30 transition-all text-[13px] leading-relaxed resize-none custom-scrollbar min-h-[64px] max-h-[200px] placeholder:text-outline-variant"
              rows={1}
            />
            <div className="absolute right-3 bottom-3 flex items-center gap-2">
              <button className="p-2 text-outline-variant hover:text-primary transition-colors hover:bg-primary/5 rounded-xl">
                 <span className="material-symbols-outlined text-[20px]">attach_file</span>
              </button>
              <button 
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || isTyping}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-headline text-[10px] uppercase tracking-[0.2em] transition-all ${
                  input.trim() && !isTyping
                    ? 'bg-primary text-on-primary shadow-[0_8px_24px_rgba(255,179,181,0.2)] hover:scale-105 active:scale-95' 
                    : 'bg-white/5 text-outline-variant opacity-50 cursor-not-allowed'
                }`}
              >
                {isTyping ? <span className="material-symbols-outlined text-sm animate-spin">refresh</span> : 'Execute'}
                {!isTyping && <span className="material-symbols-outlined text-sm">send</span>}
              </button>
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between px-2">
            <span className="text-[9px] uppercase tracking-widest text-outline-variant">Command Line Protocol Active</span>
            <div className="flex items-center gap-3">
              <span className="text-[9px] uppercase tracking-widest text-outline-variant">Don Jimmy Authorized Access</span>
            </div>
          </div>
        </footer>
      </main>

      {/* Thread Sidebar */}
      <AnimatePresence mode="wait">
        {activeThreadId && <ThreadPanel key={activeThreadId} />}
      </AnimatePresence>
    </div>
  </div>
  );
}

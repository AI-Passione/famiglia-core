import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useTerminal } from './TerminalContext';

export function ThreadPanel() {
  const { 
    activeChatId, 
    chats, 
    activeThreadId, 
    closeThread, 
    sendMessage 
  } = useTerminal();
  
  const [threadInput, setThreadInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const activeChat = chats[activeChatId];
  const parentMessage = activeChat?.messages.find(m => m.db_id === activeThreadId);
  const threadMessages = activeChat?.messages.filter(m => m.parent_id === activeThreadId) || [];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [threadMessages.length]);

  const handleSend = () => {
    if (!threadInput.trim() || !activeThreadId) return;
    sendMessage(threadInput, activeThreadId);
    setThreadInput('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!activeThreadId) return null;

  return (
    <motion.aside 
      initial={{ x: '100%' }}
      animate={{ x: 0 }}
      exit={{ x: '100%' }}
      transition={{ type: 'spring', damping: 25, stiffness: 200 }}
      className="w-96 border-l border-outline/10 bg-surface-container-low/95 backdrop-blur-xl flex flex-col shadow-2xl z-20"
    >
      {/* Header */}
      <div className="p-4 border-b border-outline/10 flex items-center justify-between bg-surface-container-lowest/40">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-primary text-sm">forum</span>
          <h2 className="font-headline text-sm italic tracking-tight text-on-surface">Thread</h2>
        </div>
        <button 
          onClick={closeThread}
          className="p-1.5 hover:bg-white/5 rounded-lg transition-colors text-outline hover:text-on-surface"
        >
          <span className="material-symbols-outlined text-sm">close</span>
        </button>
      </div>

      {/* Main Message */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
        {parentMessage && (
          <div className="pb-6 border-b border-outline/5">
             <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full overflow-hidden border border-outline/10 bg-background">
                  <img src={parentMessage.avatar || '/placeholder.png'} alt="avatar" className="w-full h-full object-cover grayscale" />
                </div>
                <span className="text-[10px] font-headline uppercase tracking-widest text-primary opacity-80">{parentMessage.speaker}</span>
             </div>
             <div className="p-4 rounded-2xl bg-primary/5 border border-primary/10 text-[13px] leading-relaxed italic text-on-surface/90">
               {parentMessage.content}
             </div>
          </div>
        )}

        {/* Replies */}
        <div className="space-y-6">
          {threadMessages.map((msg) => {
            const isUser = msg.type === 'user';
            return (
              <motion.div 
                key={msg.id}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
              >
                {!isUser && (
                  <div className="w-6 h-6 rounded-full overflow-hidden shrink-0 mt-1 border border-outline/5 bg-background">
                    <img src={msg.avatar} alt="avatar" className="w-full h-full object-cover grayscale" />
                  </div>
                )}
                <div className={`max-w-[85%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
                  <div className="flex items-center gap-2 mb-1 px-1">
                    <span className="text-[9px] font-headline uppercase tracking-widest text-outline">{msg.speaker}</span>
                  </div>
                  <div className={`p-3 rounded-2xl text-[12px] leading-relaxed ${isUser 
                    ? 'bg-primary/10 text-on-surface border border-primary/20' 
                    : 'bg-surface-container-high/40 text-on-surface border border-outline/5'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              </motion.div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="p-4 bg-surface-container-lowest/50 border-t border-outline/10">
        <div className="relative">
          <textarea
            value={threadInput}
            onChange={(e) => setThreadInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Reply to thread..."
            className="w-full bg-surface-container/30 border border-outline/10 rounded-xl p-3 pr-12 focus:ring-0 focus:border-primary/30 transition-all text-[12px] leading-relaxed resize-none custom-scrollbar min-h-[48px] max-h-[120px] placeholder:text-outline-variant"
            rows={1}
          />
          <button 
            onClick={handleSend}
            disabled={!threadInput.trim()}
            className="absolute right-2 bottom-2 p-1.5 text-primary hover:bg-primary/10 rounded-lg transition-all disabled:opacity-30"
          >
            <span className="material-symbols-outlined text-[18px]">send</span>
          </button>
        </div>
      </div>
    </motion.aside>
  );
}

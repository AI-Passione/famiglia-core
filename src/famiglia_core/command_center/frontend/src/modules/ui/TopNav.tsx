import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNotifications, type AppNotification } from '../NotificationContext';

interface NavIconButtonProps {
  icon: string;
  badge?: number;
  onClick?: () => void;
  active?: boolean;
}

function NavIconButton({ icon, badge, onClick, active }: NavIconButtonProps) {
  return (
    <button 
      onClick={onClick}
      className={`relative p-2 rounded-full transition-all duration-300 ${active ? 'bg-[#ffb3b5]/10 text-[#ffb3b5]' : 'text-[#ffb3b5]/60 hover:text-[#ffb3b5] hover:bg-white/5 hover:scale-110 active:opacity-80'}`}
    >
      <span className="material-symbols-outlined">{icon}</span>
      {badge !== undefined && badge > 0 && (
        <span className="absolute top-1 right-1 w-4 h-4 bg-[#ffb3b5] text-[#131313] text-[10px] font-black rounded-full flex items-center justify-center shadow-[0_0_12px_rgba(255,179,181,0.5)]">
          {badge > 9 ? '9+' : badge}
        </span>
      )}
    </button>
  );
}

export function TopNav() {
  const [showNotifications, setShowNotifications] = useState(false);
  const { notifications, unreadCount, markAllAsRead, clearNotifications } = useNotifications();

  return (
    <header className="fixed top-0 w-full z-50 flex justify-between items-center px-8 h-16 bg-[#131111]/80 backdrop-blur-xl border-b border-white/5 shadow-2xl">
      <div className="flex items-center gap-4 group">
        <div className="relative">
          <div className="absolute -inset-1 bg-gradient-to-r from-[#ffb3b5] to-[#f59e0b] rounded-full blur opacity-20 group-hover:opacity-40 transition duration-1000 group-hover:duration-200"></div>
          <img 
            src="/logo.png" 
            alt="Famiglia Core Logo" 
            className="relative h-9 w-9 rounded-full border border-white/10"
          />
        </div>
        <div className="flex items-center gap-3">
          <span className="font-headline italic text-2xl text-[#ffb3b5] drop-shadow-[0_0_8px_rgba(255,179,181,0.3)]">
            Famiglia Core
          </span>
          <a
            href="https://github.com/AI-Passione/famiglia-core"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 hover:border-[#ffb3b5]/30 transition-all duration-300 group/github"
            title="View Source on GitHub"
          >
            <svg className="w-4.5 h-4.5 group-hover/github:scale-110 transition-all duration-300">
              <use href="/icons.svg#github-icon" />
            </svg>
          </a>
        </div>
      </div>

      <div className="hidden md:flex items-center space-x-6">
        <div className="flex items-center gap-2 relative">
          <NavIconButton icon="search" />
          
          <div className="relative">
            <NavIconButton 
              icon="notifications" 
              badge={unreadCount} 
              active={showNotifications}
              onClick={() => {
                setShowNotifications(!showNotifications);
                if (!showNotifications && unreadCount > 0) {
                  // Mark as read after a short delay when opening
                  setTimeout(markAllAsRead, 1000);
                }
              }} 
            />
            
            <AnimatePresence>
              {showNotifications && (
                <>
                  <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-[-1]"
                    onClick={() => setShowNotifications(false)}
                  />
                  <motion.div
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    className="absolute right-0 mt-4 w-80 bg-[#1a1818] border border-white/10 rounded-2xl shadow-[0_24px_48px_rgba(0,0,0,0.5)] overflow-hidden"
                  >
                    <div className="p-4 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
                      <h3 className="font-headline text-[10px] font-bold uppercase tracking-widest text-[#ffb3b5]">Operational Alerts</h3>
                      <button onClick={clearNotifications} className="font-label text-[8px] uppercase tracking-widest text-outline hover:text-white transition-colors">Clear All</button>
                    </div>
                    
                    <div className="max-h-[400px] overflow-y-auto custom-scrollbar">
                      {notifications.length === 0 ? (
                        <div className="p-10 text-center">
                          <span className="material-symbols-outlined text-white/5 text-4xl block mb-2">notifications_off</span>
                          <p className="font-body text-[10px] text-outline/40 italic">No recent intel reports.</p>
                        </div>
                      ) : (
                        notifications.map((n: AppNotification) => (
                          <div 
                            key={n.id} 
                            className={`p-4 border-b border-white/5 hover:bg-white/[0.03] transition-colors cursor-default ${!n.read ? 'bg-[#ffb3b5]/[0.02]' : ''}`}
                          >
                            <div className="flex gap-3">
                              <span className={`material-symbols-outlined text-sm mt-0.5 ${
                                n.type === 'success' ? 'text-green-400' : 
                                n.type === 'error' ? 'text-red-400' : 
                                'text-[#ffb3b5]'
                              }`}>
                                {n.type === 'success' ? 'check_circle' : n.type === 'error' ? 'error' : 'info'}
                              </span>
                              <div className="flex-1 min-w-0">
                                <p className="font-headline text-[11px] font-bold text-white mb-0.5 truncate">{n.title}</p>
                                <p className="font-body text-[10px] text-outline/60 leading-relaxed line-clamp-2">{n.message}</p>
                                <p className="font-label text-[8px] text-outline/30 uppercase mt-2">{new Date(n.timestamp).toLocaleTimeString()}</p>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </motion.div>
                </>
              )}
            </AnimatePresence>
          </div>
          
          <NavIconButton icon="account_circle" />
        </div>
      </div>
    </header>
  );
}


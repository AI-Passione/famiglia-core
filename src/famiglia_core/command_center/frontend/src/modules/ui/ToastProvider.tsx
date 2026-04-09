import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'info' | 'error';
  agent_id?: string;
}

interface ToastContextType {
  showToast: (message: string, type?: 'success' | 'info' | 'error', agent_id?: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, type: 'success' | 'info' | 'error' = 'info', agent_id?: string) => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts((prev) => [...prev, { id, message, type, agent_id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed top-24 right-8 z-[100] flex flex-col gap-4 pointer-events-none">
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, x: 50, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 20, scale: 0.95 }}
              className="pointer-events-auto"
            >
              <div className={`
                relative px-6 py-4 rounded-2xl border backdrop-blur-xl shadow-2xl flex items-center gap-4 min-w-[320px] max-w-md
                ${toast.type === 'success' ? 'bg-emerald-950/40 border-emerald-500/30' : 
                  toast.type === 'error' ? 'bg-red-950/40 border-red-500/30' : 
                  'bg-[#131313]/80 border-white/10'}
              `}>
                {/* Glow Effect */}
                <div className={`absolute -inset-1 rounded-2xl blur-lg opacity-20 ${
                  toast.type === 'success' ? 'bg-emerald-500' : 
                  toast.type === 'error' ? 'bg-red-500' : 
                  'bg-[#ffb3b5]'
                }`} />
                
                <div className="relative flex items-center gap-4 w-full">
                  <div className={`p-2 rounded-lg ${
                    toast.type === 'success' ? 'bg-emerald-500/20 text-emerald-400' : 
                    toast.type === 'error' ? 'bg-red-500/20 text-red-400' : 
                    'bg-[#ffb3b5]/20 text-[#ffb3b5]'
                  }`}>
                    <span className="material-symbols-outlined text-xl">
                      {toast.type === 'success' ? 'check_circle' : 
                       toast.type === 'error' ? 'report' : 
                       'notifications_active'}
                    </span>
                  </div>
                  
                  <div className="flex-1">
                    <p className="font-headline text-sm font-bold text-white tracking-tight leading-tight">
                      {toast.message}
                    </p>
                    {toast.agent_id && (
                      <p className="font-label text-[10px] uppercase tracking-widest text-[#a38b88] mt-1">
                        Reported by {toast.agent_id}
                      </p>
                    )}
                  </div>

                  <button 
                    onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))}
                    className="text-white/20 hover:text-white/60 transition-colors"
                  >
                    <span className="material-symbols-outlined text-sm">close</span>
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within a ToastProvider');
  return context;
};

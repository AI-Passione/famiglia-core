import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal } from '../Terminal';
import { useTerminal } from '../TerminalContext';

export function DirectivesTerminal() {
  const { isTerminalOpen: isOpen, setTerminalOpen: setIsOpen } = useTerminal();
  const [isMaximized, setIsMaximized] = useState(false);
  
  return (
    <div className="fixed bottom-8 right-8 z-[100] flex flex-col items-end gap-4">
      <AnimatePresence mode="wait">
        {isOpen && (
          <motion.div
            key="directives-terminal-window"
            initial={{ opacity: 0, y: 20, scale: 0.95, width: '450px', height: '600px' }}
            animate={{ 
              opacity: 1, 
              y: 0, 
              scale: 1,
              width: isMaximized ? '80vw' : '450px',
              height: isMaximized ? '80vh' : '650px'
            }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="glass-module border border-outline/20 rounded-[32px] shadow-[0px_32px_64px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col mb-4 bg-surface/90 backdrop-blur-3xl"
          >
            {/* Header Control Overlay */}
            <div className="absolute top-4 right-6 z-20 flex items-center gap-2">
              <button 
                onClick={() => setIsMaximized(!isMaximized)}
                className="p-1.5 hover:bg-white/10 rounded-full transition-colors text-outline-variant hover:text-on-surface"
                title={isMaximized ? "Minimize" : "Maximize"}
              >
                {isMaximized ? <span className="material-symbols-outlined text-[18px]">close_fullscreen</span> : <span className="material-symbols-outlined text-[18px]">open_in_full</span>}
              </button>
              <button 
                onClick={() => setIsOpen(false)}
                className="p-1.5 hover:bg-white/10 rounded-full transition-colors text-outline-variant hover:text-on-surface"
                title="Close"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>

            {/* Compressed Terminal Instance */}
            <div className="flex-1 overflow-hidden">
               <Terminal variant="compact" />
            </div>

            {/* Link to Full Page */}
            <div className="px-6 py-2 bg-primary/5 border-t border-outline/5 flex justify-between items-center bg-surface-container-low/50">
               <span className="text-[9px] uppercase tracking-widest text-outline-variant font-bold">Secure Mission Feed</span>
               <button 
                  onClick={() => window.open('/terminal.html', '_blank')}
                  className="text-[9px] uppercase tracking-widest text-primary font-bold hover:underline flex items-center gap-1 group"
               >
                  Open Full Command Center
                  <span className="material-symbols-outlined text-[12px] group-hover:translate-x-1 transition-transform">arrow_forward</span>
               </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* FAB Button */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
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

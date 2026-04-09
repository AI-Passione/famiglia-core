import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { GraphDefinition } from '../../types';
import { API_BASE } from '../../config';

interface OperationsHubProps {
  graphs: GraphDefinition[];
}

export function OperationsHub({ graphs }: OperationsHubProps) {
  const [executing, setExecuting] = useState<Record<string, boolean>>({});
  const [messages, setMessages] = useState<Record<string, string>>({});

  const handleExecute = async (graphId: string) => {
    setExecuting(prev => ({ ...prev, [graphId]: true }));
    setMessages(prev => ({ ...prev, [graphId]: '' }));

    try {
      const response = await fetch(`${API_BASE}/operations/graphs/${graphId}/execute`, {
        method: 'POST',
      });
      
      if (response.ok) {
        const data = await response.json();
        setMessages(prev => ({ ...prev, [graphId]: data.message || 'Directive executed.' }));
      } else {
        setMessages(prev => ({ ...prev, [graphId]: 'Failed to execute directive.' }));
      }
    } catch (error) {
      console.error('Error executing directive:', error);
      setMessages(prev => ({ ...prev, [graphId]: 'Error connecting to Command Center.' }));
    } finally {
      setTimeout(() => {
        setExecuting(prev => ({ ...prev, [graphId]: false }));
        // keep message up for a bit then clear
        setTimeout(() => setMessages(prev => ({ ...prev, [graphId]: '' })), 5000);
      }, 1000);
    }
  };

  const actionGraphs = (graphs || []).slice(0, 3); // show top 3 for brevity in Situation Room

  return (
    <div className="bg-surface-container-highest p-6 h-full flex flex-col border border-primary/10 relative shadow-[inset_0_0_24px_rgba(255,179,181,0.02)]">
      <div className="absolute top-0 right-0 p-4 opacity-10">
        <span className="material-symbols-outlined text-[64px]">bolt</span>
      </div>
      <div className="flex items-center justify-between mb-6 relative z-10">
        <h3 className="font-headline text-xl text-on-surface">Actionable Directives</h3>
        <span className="material-symbols-outlined text-primary">crisis_alert</span>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto custom-scrollbar relative z-10 pr-2">
        {actionGraphs.length > 0 ? (
          actionGraphs.map((graph, idx) => (
            <motion.div 
              key={graph.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.1 }}
              className="p-4 bg-surface-container-low border border-outline/10 rounded-xl hover:border-primary/30 transition-all group"
            >
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h4 className="font-headline text-sm text-on-surface mb-1 group-hover:text-primary transition-colors">{graph.name}</h4>
                  <span className="font-label text-[9px] uppercase tracking-widest text-outline">Operation: {graph.id}</span>
                </div>
                <button
                  onClick={() => handleExecute(graph.id)}
                  disabled={executing[graph.id]}
                  className={`px-4 py-2 font-label text-[10px] uppercase tracking-[0.2em] rounded-sm transition-all flex items-center gap-2 ${
                    executing[graph.id] 
                      ? 'bg-outline-variant text-on-surface cursor-not-allowed' 
                      : 'bg-primary text-on-primary hover:scale-105 active:scale-95 shadow-[0_4px_12px_rgba(255,179,181,0.2)]'
                  }`}
                >
                  {executing[graph.id] ? (
                     <span className="material-symbols-outlined text-[14px] animate-spin">refresh</span>
                  ) : (
                     <span className="material-symbols-outlined text-[14px]">play_arrow</span>
                  )}
                  {executing[graph.id] ? 'Deploying...' : 'Execute'}
                </button>
              </div>
              <AnimatePresence>
                {messages[graph.id] && (
                  <motion.div 
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-2 text-[10px] font-label text-tertiary italic tracking-wider flex items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-[12px]">check_circle</span>
                    {messages[graph.id]}
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))
        ) : (
           <div className="text-center py-10 opacity-50 flex flex-col items-center">
             <span className="material-symbols-outlined text-[32px] mb-2">check_box</span>
             <p className="font-label text-xs uppercase tracking-widest text-outline">No pending directives</p>
           </div>
        )}
      </div>
    </div>
  );
}

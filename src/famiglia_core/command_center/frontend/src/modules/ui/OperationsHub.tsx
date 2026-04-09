import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { GraphDefinition } from '../../types';
import { API_BASE } from '../../config';

interface OperationsHubProps {
  graphs: GraphDefinition[];
  onExecuteDirective: () => void;
}


export function OperationsHub({ graphs, onExecuteDirective }: OperationsHubProps) {
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
      setMessages(prev => ({ ...prev, [graphId]: 'Error connecting to Command Center.' }));
    } finally {
      setTimeout(() => {
        setExecuting(prev => ({ ...prev, [graphId]: false }));
        setTimeout(() => setMessages(prev => ({ ...prev, [graphId]: '' })), 5000);
      }, 1000);
    }
  };

  const actionGraphs = (graphs || []).slice(0, 3);

  return (
    <div className="bg-surface-container-highest p-6 flex flex-col border border-primary/10 relative shadow-[inset_0_0_24px_rgba(255,179,181,0.02)] rounded-2xl gap-6">


      {/* ── Execute Directives ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-sm">crisis_alert</span>
            <h3 className="font-headline text-lg text-on-surface">Directives</h3>
          </div>
          <button 
            onClick={onExecuteDirective}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 transition-all font-label text-[10px] uppercase tracking-widest"
          >
            <span className="material-symbols-outlined text-sm">bolt</span>
            Dispatch
          </button>
        </div>

        {actionGraphs.length > 0 ? (
          <div className="space-y-3">
            {actionGraphs.map((graph, idx) => (
              <motion.div
                key={graph.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: idx * 0.1 }}
                className="p-3 bg-surface-container-low border border-outline/10 rounded-xl hover:border-primary/30 transition-all group flex justify-between items-center"
              >
                <div>
                  <h4 className="font-headline text-sm text-on-surface group-hover:text-primary transition-colors">{graph.name}</h4>
                  <span className="font-label text-[9px] uppercase tracking-widest text-outline">{graph.id}</span>
                </div>
                <button
                  onClick={() => handleExecute(graph.id)}
                  disabled={executing[graph.id]}
                  className={`px-3 py-1.5 font-label text-[10px] uppercase tracking-[0.2em] rounded-lg transition-all flex items-center gap-1.5 ${
                    executing[graph.id]
                      ? 'bg-outline-variant text-on-surface cursor-not-allowed'
                      : 'bg-primary text-on-primary hover:scale-105 active:scale-95 shadow-[0_4px_12px_rgba(255,179,181,0.2)]'
                  }`}
                >
                  {executing[graph.id]
                    ? <span className="material-symbols-outlined text-[14px] animate-spin">refresh</span>
                    : <span className="material-symbols-outlined text-[14px]">play_arrow</span>
                  }
                  {executing[graph.id] ? 'Deploying...' : 'Execute'}
                </button>
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6 opacity-50 flex flex-col items-center">
            <span className="material-symbols-outlined text-[28px] mb-2">check_box</span>
            <p className="font-label text-xs uppercase tracking-widest text-outline">No pending directives</p>
          </div>
        )}
        <AnimatePresence>
          {Object.entries(messages).map(([id, msg]) => msg ? (
            <motion.p
              key={id}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-2 text-[10px] font-label text-tertiary italic tracking-wider flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-[12px]">check_circle</span>
              {msg}
            </motion.p>
          ) : null)}
        </AnimatePresence>
      </div>
    </div>
  );
}

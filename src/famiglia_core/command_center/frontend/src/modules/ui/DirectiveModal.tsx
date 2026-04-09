import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GraphDefinition } from '../../types';
import { API_BASE } from '../../config';
import { useToast } from './ToastProvider';

interface DirectiveModalProps {
  isOpen: boolean;
  onClose: () => void;
  graphs: GraphDefinition[];
}

export function DirectiveModal({ isOpen, onClose, graphs }: DirectiveModalProps) {
  const [selectedGraphId, setSelectedGraphId] = useState<string | null>(null);
  const [manualPrompt, setManualPrompt] = useState('');
  const [executing, setExecuting] = useState(false);
  const { showToast } = useToast();

  const handleExecute = async () => {
    if (!selectedGraphId && !manualPrompt.trim()) return;

    setExecuting(true);
    try {
      const response = await fetch(`${API_BASE}/operations/directive/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          graph_id: selectedGraphId,
          manual_prompt: manualPrompt.trim() || undefined,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        showToast(data.message, 'success');
        
        // Close modal after a short delay
        setTimeout(() => {
          onClose();
          // Reset state
          setSelectedGraphId(null);
          setManualPrompt('');
          setExecuting(false);
        }, 800);
      } else {
        showToast('Failed to dispatch directive.', 'error');
        setExecuting(false);
      }
    } catch (error) {
      showToast('Error connecting to Command Center.', 'error');
      setExecuting(false);
    }
  };

  const categories = Array.from(new Set(graphs.map(g => g.category))).sort();

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-[#0a0a0a]/60 backdrop-blur-md"
          />

          {/* Modal Container */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            className="relative w-full max-w-2xl bg-[#131111]/90 border border-white/10 rounded-[32px] shadow-[0_32px_128px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col max-h-[90vh]"
          >
            {/* Header */}
            <div className="p-8 border-b border-white/5 flex justify-between items-start">
              <div>
                <h2 className="text-3xl font-headline font-bold text-[#ffb3b5] tracking-tight">Execute Directive</h2>
                <p className="font-body text-outline mt-1 uppercase tracking-widest text-[10px] font-bold">Strategic Mission Dispatch</p>
              </div>
              <button 
                onClick={onClose}
                className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors"
              >
                <span className="material-symbols-outlined text-outline">close</span>
              </button>
            </div>

            {/* Content Container */}
            <div className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
              
              {/* Quick Directives Section */}
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <span className="material-symbols-outlined text-[#ffb3b5] text-sm">bolt</span>
                  <h3 className="font-headline text-xs font-bold uppercase tracking-widest text-white/40">Quick Directives</h3>
                </div>
                
                <div className="space-y-6">
                  {categories.map(category => (
                    <div key={category}>
                      <h4 className="font-label text-[10px] uppercase tracking-widest text-[#a38b88] mb-3">{category}</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {graphs.filter(g => g.category === category).map(graph => (
                          <button
                            key={graph.id}
                            onClick={() => {
                                setSelectedGraphId(selectedGraphId === graph.id ? null : graph.id);
                                setManualPrompt('');
                            }}
                            className={`
                              group relative px-5 py-4 rounded-2xl border text-left transition-all duration-300
                              ${selectedGraphId === graph.id 
                                ? 'bg-[#ffb3b5]/10 border-[#ffb3b5]/40 shadow-[0_0_24px_rgba(255,179,181,0.1)]' 
                                : 'bg-white/5 border-white/5 hover:border-white/20 hover:bg-white/10'}
                            `}
                          >
                            <div className="flex justify-between items-center">
                              <span className={`font-headline text-sm font-medium ${selectedGraphId === graph.id ? 'text-[#ffb3b5]' : 'text-white'}`}>
                                {graph.name}
                              </span>
                              {selectedGraphId === graph.id && (
                                <span className="material-symbols-outlined text-[#ffb3b5] text-sm">check_circle</span>
                              )}
                            </div>
                            <p className="font-label text-[9px] uppercase tracking-widest text-outline mt-1 group-hover:text-white/40 transition-colors">
                              {graph.id}
                            </p>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* Divider */}
              <div className="flex items-center gap-4 py-2">
                <div className="h-px flex-1 bg-white/5" />
                <span className="font-label text-[10px] uppercase tracking-widest text-outline">OR</span>
                <div className="h-px flex-1 bg-white/5" />
              </div>

              {/* Manual Directive Section */}
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <span className="material-symbols-outlined text-[#ffb3b5] text-sm">edit_note</span>
                  <h3 className="font-headline text-xs font-bold uppercase tracking-widest text-white/40">Manual Directive</h3>
                </div>
                
                <div className="relative group/input">
                  <textarea
                    value={manualPrompt}
                    onChange={(e) => {
                        setManualPrompt(e.target.value);
                        setSelectedGraphId(null);
                    }}
                    placeholder="Enter custom instructions for the Famiglia..."
                    className="w-full bg-white/5 border border-white/5 rounded-2xl p-6 font-body text-sm text-white placeholder:text-outline/40 focus:outline-none focus:border-[#ffb3b5]/40 focus:bg-[#ffb3b5]/5 transition-all resize-none h-32"
                  />
                  {/* Decorative corner */}
                  <div className="absolute top-0 right-0 w-8 h-8 pointer-events-none overflow-hidden rounded-tr-2xl">
                    <div className="absolute top-0 right-0 w-12 h-12 bg-gradient-to-bl from-[#ffb3b5]/10 to-transparent rotate-45 transform translate-x-1/2 -translate-y-1/2" />
                  </div>
                </div>
              </section>
            </div>

            {/* Footer */}
            <div className="p-8 border-t border-white/5 bg-[#0a0a0a]/40 backdrop-blur-sm">
              <button
                onClick={handleExecute}
                disabled={executing || (!selectedGraphId && !manualPrompt.trim())}
                className={`
                  w-full py-5 rounded-2xl font-label text-xs uppercase tracking-[0.3em] font-black flex items-center justify-center gap-3 transition-all duration-500
                  ${executing || (!selectedGraphId && !manualPrompt.trim())
                    ? 'bg-white/5 text-outline cursor-not-allowed'
                    : 'bg-[#ffb3b5] text-[#131111] hover:shadow-[0_0_48px_rgba(255,179,181,0.3)] hover:scale-[1.01] active:scale-[0.99]'}
                `}
              >
                {executing ? (
                  <>
                    <span className="material-symbols-outlined animate-spin">refresh</span>
                    Dispatching...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined">send</span>
                    Dispatch Directive
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { GraphDefinition } from '../../types';
import { API_BASE } from '../../config';
import { useToast } from './ToastProvider';

interface DirectiveModalProps {
  isOpen: boolean;
  onClose: () => void;
  graphs: GraphDefinition[];
}

export function DirectiveModal({ isOpen, onClose, graphs }: DirectiveModalProps) {
  const [selectedGraphId, setSelectedGraphId] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
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

  const categoryOrder = ["Market Research", "Product Development", "Analytics"];
  const categories: string[] = Array.from(new Set(graphs.map(g => g.category).filter((c): c is string => !!c))).sort((a, b) => {
    const indexA = categoryOrder.indexOf(a);
    const indexB = categoryOrder.indexOf(b);
    if (indexA !== -1 && indexB !== -1) return indexA - indexB;
    if (indexA !== -1) return -1;
    if (indexB !== -1) return 1;
    return a.localeCompare(b);
  });

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
            className="relative w-full max-w-2xl bg-[#131111]/95 border border-white/10 rounded-[32px] shadow-[0_32px_128px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col max-h-[95vh]"
          >
            {/* Header */}
            <div className="p-4 border-b border-white/5 flex justify-between items-start">
              <div>
                <h2 className="text-xl font-headline font-bold text-[#ffb3b5] tracking-tight">Execute Directive</h2>
                <p className="font-body text-outline mt-0.5 uppercase tracking-widest text-[8px] font-bold">Strategic Mission Dispatch</p>
              </div>
              <button 
                onClick={onClose}
                className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors"
              >
                <span className="material-symbols-outlined text-outline">close</span>
              </button>
            </div>

            {/* Content Container */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
              
              {/* Quick Directives Section with Tabbed Nav */}
              <section className="space-y-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="material-symbols-outlined text-[#ffb3b5] text-[14px]">bolt</span>
                  <h3 className="font-headline text-[9px] font-bold uppercase tracking-widest text-white/40">Select Mission Type</h3>
                </div>
                
                <div className="flex flex-wrap gap-2">
                  {categories.map(category => (
                    <button
                      key={category}
                      onClick={() => setActiveCategory(prev => prev === category ? null : category)}
                      className={`
                        px-4 py-2 rounded-full font-label text-[9px] uppercase tracking-widest transition-all duration-300 border
                        ${activeCategory === category 
                          ? 'bg-[#ffb3b5] text-[#131111] border-[#ffb3b5] shadow-[0_0_24px_rgba(255,179,181,0.2)]' 
                          : 'bg-white/5 text-outline border-white/5 hover:border-white/20 hover:bg-white/10'}
                      `}
                    >
                      {category}
                    </button>
                  ))}
                </div>

                {/* Sub-features expansion */}
                <AnimatePresence mode="wait">
                  {activeCategory && (
                    <motion.div
                      key={activeCategory}
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-2 border-t border-white/5 mt-2">
                        {graphs.filter(g => g.category === activeCategory).map(graph => (
                          <button
                            key={graph.id}
                            onClick={() => {
                                setSelectedGraphId(prev => prev === graph.id ? null : graph.id);
                                setManualPrompt('');
                            }}
                            className={`
                              group relative px-4 py-3 rounded-xl border text-left transition-all duration-300
                              ${selectedGraphId === graph.id 
                                ? 'bg-[#ffb3b5]/10 border-[#ffb3b5]/40 shadow-[0_0_16px_rgba(255,179,181,0.1)]' 
                                : 'bg-white/5 border-white/5 hover:border-white/20 hover:bg-white/10'}
                            `}
                          >
                            <div className="flex justify-between items-center">
                              <span className={`font-headline text-xs font-medium ${selectedGraphId === graph.id ? 'text-[#ffb3b5]' : 'text-white'}`}>
                                {graph.name}
                              </span>
                              {selectedGraphId === graph.id && (
                                <span className="material-symbols-outlined text-[#ffb3b5] text-[14px]">check_circle</span>
                              )}
                            </div>
                            <p className="font-label text-[8px] uppercase tracking-widest text-outline mt-0.5 group-hover:text-white/40 transition-colors">
                              {graph.id}
                            </p>
                          </button>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </section>

              {/* Divider */}
              <div className="flex items-center gap-4 py-2">
                <div className="h-px flex-1 bg-white/5" />
                <span className="font-label text-[10px] uppercase tracking-widest text-outline">OR</span>
                <div className="h-px flex-1 bg-white/5" />
              </div>

               {/* Manual Directive Section */}
              <section>
                <div className="flex items-center gap-2 mb-2">
                  <span className="material-symbols-outlined text-[#ffb3b5] text-[14px]">edit_note</span>
                  <h3 className="font-headline text-[9px] font-bold uppercase tracking-widest text-white/40">Manual Directive</h3>
                </div>
                
                <div className="relative group/input">
                  <textarea
                    value={manualPrompt}
                    onChange={(e) => {
                        setManualPrompt(e.target.value);
                        setSelectedGraphId(null);
                    }}
                    placeholder="Enter custom instructions for the Famiglia..."
                    className="w-full bg-white/5 border border-white/5 rounded-xl p-3 font-body text-[11px] text-white placeholder:text-outline/40 focus:outline-none focus:border-[#ffb3b5]/40 focus:bg-[#ffb3b5]/5 transition-all resize-none h-20"
                  />
                  {/* Decorative corner */}
                  <div className="absolute top-0 right-0 w-8 h-8 pointer-events-none overflow-hidden rounded-tr-2xl">
                    <div className="absolute top-0 right-0 w-12 h-12 bg-gradient-to-bl from-[#ffb3b5]/10 to-transparent rotate-45 transform translate-x-1/2 -translate-y-1/2" />
                  </div>
                </div>
              </section>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-white/5 bg-[#0a0a0a]/60 backdrop-blur-sm">
              <button
                onClick={handleExecute}
                disabled={executing || (!selectedGraphId && !manualPrompt.trim())}
                className={`
                  w-full py-3.5 rounded-xl font-label text-[9px] uppercase tracking-[0.3em] font-black flex items-center justify-center gap-3 transition-all duration-500
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

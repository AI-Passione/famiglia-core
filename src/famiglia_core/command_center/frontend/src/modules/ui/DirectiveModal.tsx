import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { GraphDefinition } from '../../types';
import { API_BASE } from '../../config';
import { useToast } from './ToastProvider';
import { useTerminal } from '../TerminalContext';

interface DirectiveModalProps {
  isOpen: boolean;
  onClose: () => void;
  graphs: GraphDefinition[];
}

export function DirectiveModal({ isOpen, onClose, graphs }: DirectiveModalProps) {
  const [selectedGraphId, setSelectedGraphId] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [manualPrompt, setManualPrompt] = useState('');
  const [specification, setSpecification] = useState('');
  const [isManualExpanded, setIsManualExpanded] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [successData, setSuccessData] = useState<{ id: string, message: string, agent: string } | null>(null);
  const { showToast } = useToast();
  const { setTerminalOpen, addExternalAgentMessage } = useTerminal();

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
          specification: specification.trim() || undefined,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        
        // Populate success view
        setSuccessData({
          id: data.message.match(/ML-\d+/)?.[0] || 'ML-ID',
          message: data.acknowledgement || "Directive received and queued for execution.",
          agent: data.agent_id || "Alfredo"
        });

        // Instant Feedback: Add agent acknowledgement to terminal immediately
        if (data.acknowledgement && data.agent_id) {
          addExternalAgentMessage(data.acknowledgement, data.agent_id);
        }
        
        setExecuting(false);
      } else {
        showToast('Failed to dispatch directive.', 'error');
        setExecuting(false);
      }
    } catch (error) {
      showToast('Error connecting to Command Center.', 'error');
      setExecuting(false);
    }
  };

  const handleFinish = () => {
    setTerminalOpen(true);
    onClose();
    // Reset state after closure animation
    setTimeout(() => {
      setSuccessData(null);
      setSelectedGraphId(null);
      setManualPrompt('');
      setSpecification('');
      setIsManualExpanded(false);
    }, 500);
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
              
              <AnimatePresence mode="wait">
                {successData ? (
                  <motion.div
                    key="success-view"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className="py-8 px-4 text-center space-y-6"
                  >
                    <div className="flex justify-center">
                      <div className="w-20 h-20 rounded-full bg-[#ffb3b5]/10 flex items-center justify-center relative">
                        <motion.div 
                          className="absolute inset-0 rounded-full border border-[#ffb3b5]/40"
                          animate={{ scale: [1, 1.2, 1], opacity: [0.4, 0, 0.4] }}
                          transition={{ duration: 2, repeat: Infinity }}
                        />
                        <span className="material-symbols-outlined text-[#ffb3b5] text-4xl">check_circle</span>
                      </div>
                    </div>
                    
                    <div>
                      <h3 className="font-headline text-2xl font-bold text-white mb-2">Mission Dispatched</h3>
                      <div className="flex items-center justify-center gap-2">
                        <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-full font-label text-[10px] tracking-widest text-[#ffb3b5]">
                          TRACKING ID: {successData.id}
                        </span>
                        <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-full font-label text-[10px] tracking-widest text-outline">
                          AGENT: {successData.agent.toUpperCase()}
                        </span>
                      </div>
                    </div>

                    <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6 text-left relative overflow-hidden group">
                       <div className="absolute top-0 right-0 p-4 opacity-5">
                          <span className="material-symbols-outlined text-6xl">chat_bubble</span>
                       </div>
                       <p className="font-body text-xs text-outline/60 italic mb-2">Initial Acknowledgement:</p>
                       <p className="font-body text-[13px] text-white leading-relaxed relative z-10">
                        "{successData.message}"
                       </p>
                    </div>

                    <p className="font-body text-[10px] text-outline/40 italic">
                      Live reports will be streamed to the #command-center channel.
                    </p>
                  </motion.div>
                ) : (
                  <motion.div 
                    key="form-view"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="space-y-6"
                   >
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
                                      if (selectedGraphId !== graph.id) setManualPrompt('');
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

                      {/* Specification Field (Appears only when graph is selected) */}
                      <AnimatePresence>
                        {selectedGraphId && (
                          <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="mt-4 p-4 bg-[#ffb3b5]/5 border border-[#ffb3b5]/20 rounded-2xl relative"
                          >
                            <div className="flex items-center gap-2 mb-2">
                              <span className="material-symbols-outlined text-[#ffb3b5] text-[14px]">psychology_alt</span>
                              <h4 className="font-headline text-[9px] font-bold uppercase tracking-widest text-[#ffb3b5]/60">Mission Specifications</h4>
                            </div>
                            <textarea
                              value={specification}
                              onChange={(e) => setSpecification(e.target.value)}
                              placeholder="Enter mission specific constraints or parameters (e.g., 'Targeting the luxury tech niche')..."
                              className="w-full bg-white/5 border border-white/5 rounded-xl p-3 font-body text-[11px] text-white placeholder:text-outline/30 focus:outline-none focus:border-[#ffb3b5]/30 transition-all resize-none h-20"
                            />
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </section>

                    {/* Divider */}
                    <div className="flex items-center gap-4">
                      <div className="h-px flex-1 bg-white/5" />
                      <span className="font-label text-[8px] uppercase tracking-widest text-outline-variant">Alternatively</span>
                      <div className="h-px flex-1 bg-white/5" />
                    </div>

                    {/* Manual Directive Section (Collapsed by default) */}
                    <section className="border border-white/5 rounded-2xl overflow-hidden bg-white/[0.02]">
                      <button
                        onClick={() => setIsManualExpanded(!isManualExpanded)}
                        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors group"
                      >
                        <div className="flex items-center gap-3">
                          <span className={`material-symbols-outlined text-sm transition-colors ${isManualExpanded ? 'text-[#ffb3b5]' : 'text-outline/60 group-hover:text-outline'}`}>
                            edit_note
                          </span>
                          <h3 className={`font-headline text-[10px] font-bold uppercase tracking-widest transition-colors ${isManualExpanded ? 'text-white' : 'text-white/40 group-hover:text-white/60'}`}>
                            Custom Ad-hoc Directive
                          </h3>
                        </div>
                        <span className={`material-symbols-outlined transition-transform duration-500 text-outline/40 ${isManualExpanded ? 'rotate-180 text-[#ffb3b5]' : ''}`}>
                          expand_more
                        </span>
                      </button>
                      
                      <AnimatePresence>
                        {isManualExpanded && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="p-4 pt-0">
                              <div className="relative group/input mt-2">
                                <textarea
                                  value={manualPrompt}
                                  onChange={(e) => {
                                      setManualPrompt(e.target.value);
                                      setSelectedGraphId(null);
                                      setSpecification('');
                                      setActiveCategory(null);
                                  }}
                                  placeholder="Enter fully custom, unstructured instructions..."
                                  className="w-full bg-black/40 border border-white/5 rounded-xl p-3 font-body text-[11px] text-white placeholder:text-outline/40 focus:outline-none focus:border-[#ffb3b5]/40 transition-all resize-none h-24"
                                />
                              </div>
                              <p className="mt-2 font-body text-[9px] text-outline/40 italic">
                                * Best for one-off tasks not covered by standard operational graphs.
                              </p>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </section>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-white/5 bg-[#0a0a0a]/60 backdrop-blur-sm">
              {successData ? (
                <button
                  onClick={handleFinish}
                  className="w-full py-3.5 rounded-xl font-label text-[9px] uppercase tracking-[0.3em] font-black flex items-center justify-center gap-3 transition-all duration-500 bg-white/5 text-white hover:bg-white/10 active:scale-[0.98]"
                >
                  <span className="material-symbols-outlined">terminal</span>
                  Monitore in Terminal
                </button>
              ) : (
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
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

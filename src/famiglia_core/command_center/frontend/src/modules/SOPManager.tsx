import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { SOPWorkflow } from '../types';
import { API_BASE } from '../config';

interface SOPManagerProps {
  onEdit: (workflow: SOPWorkflow) => void;
  onCreate: () => void;
}

export function SOPManager({ onEdit, onCreate }: SOPManagerProps) {
  const [workflows, setWorkflows] = useState<SOPWorkflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [executingId, setExecutingId] = useState<number | null>(null);

  const fetchWorkflows = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/sop/workflows`);
      if (res.ok) {
        const data = await res.json();
        setWorkflows(data);
      }
    } catch (err) {
      console.error("Error fetching SOPs:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWorkflows();
  }, [fetchWorkflows]);

  const handleExecute = async (id: number) => {
    setExecutingId(id);
    try {
      const res = await fetch(`${API_BASE}/sop/workflows/${id}/execute`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        console.log(data.message);
      }
    } catch (err) {
      console.error("Error executing SOP:", err);
    } finally {
      setTimeout(() => setExecutingId(null), 1000);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Are you sure you want to delete this SOP?")) return;
    
    try {
      const res = await fetch(`${API_BASE}/sop/workflows/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setWorkflows(prev => prev.filter(w => w.id !== id));
      }
    } catch (err) {
      console.error("Error deleting SOP:", err);
    }
  };

  return (
    <div className="space-y-8 min-h-[600px]">
      <div className="flex justify-between items-end">
        <div>
          <h3 className="font-headline text-2xl text-on-surface">Standard Operating Procedures</h3>
          <p className="font-label text-[10px] text-tertiary uppercase tracking-[0.2em] mt-1 opacity-70">
            Manual Governance & Structural Intelligence // 0xSOP
          </p>
        </div>
        <button
          onClick={onCreate}
          className="bg-primary/10 text-primary border border-primary/20 px-6 py-2 font-label text-[10px] uppercase tracking-widest hover:bg-primary/20 transition-all flex items-center space-x-2"
        >
          <span className="material-symbols-outlined text-sm">add</span>
          <span>Draft New SOP</span>
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin"></div>
        </div>
      ) : (
        <div className="space-y-12">
          {(() => {
            // These keys match the snake_case values in the database (market_research, product_development, analytics)
            const categoriesOrder = ["market_research", "product_development", "analytics"];
            
            // Helpful titles for internal category keys
            const categoryTitles: Record<string, string> = {
              "market_research": "Market Research",
              "product_development": "Product Development",
              "analytics": "Analytics"
            };

            // Group workflows by category
            const grouped = workflows.reduce((acc, wf) => {
              const cat = wf.category || "General";
              if (!acc[cat]) acc[cat] = [];
              acc[cat].push(wf);
              return acc;
            }, {} as Record<string, SOPWorkflow[]>);

            // Get all categories, starting with ordered ones
            const allCategories = [
              ...categoriesOrder.filter(c => grouped[c]),
              ...Object.keys(grouped).filter(c => !categoriesOrder.includes(c) && grouped[c].length > 0)
            ];

            if (workflows.length === 0) {
              return (
                <div className="py-32 text-center bg-surface-container-low/30 border border-dashed border-outline-variant/20">
                  <span className="material-symbols-outlined text-4xl text-outline/30 mb-4 block">account_tree</span>
                  <p className="font-label text-xs text-[#a38b88] uppercase tracking-[0.4em]">No Structural Intelligence Detected</p>
                  <button 
                    onClick={onCreate}
                    className="mt-6 text-primary font-label text-[10px] uppercase tracking-widest hover:underline"
                  >
                    Initialize First Protocol
                  </button>
                </div>
              );
            }

            return allCategories.map((category) => (
              <div key={category} className="space-y-6">
                <div className="flex items-center space-x-4">
                  <h4 className="font-label text-[10px] text-primary uppercase tracking-[0.3em] font-bold">
                    {categoryTitles[category] || category.replace(/_/g, ' ').replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase())}
                  </h4>
                  <div className="h-[1px] flex-1 bg-outline-variant/10"></div>
                  <span className="font-mono text-[9px] text-outline opacity-50">
                    {grouped[category].length} {grouped[category].length === 1 ? 'PROTOCOL' : 'PROTOCOLS'}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  <AnimatePresence>
                    {grouped[category].map((workflow, idx) => (
                      <motion.div
                        key={workflow.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        transition={{ duration: 0.4, delay: idx * 0.05 }}
                        className="bg-surface-container-low border border-outline-variant/10 p-6 flex flex-col justify-between group relative overflow-hidden"
                      >
                        {/* Decorative Background Glow */}
                        <div className="absolute -right-12 -top-12 w-32 h-32 bg-primary/5 rounded-full blur-3xl group-hover:bg-primary/10 transition-all duration-700"></div>
                        
                        <div className="space-y-4 relative z-10">
                          <div className="flex justify-between items-start">
                            <span className="font-label text-[8px] text-tertiary uppercase tracking-[0.2em] px-2 py-0.5 bg-surface-container-highest border border-outline-variant/10">
                              {categoryTitles[category] || category.replace(/_/g, ' ')}
                            </span>
                            <div className="flex space-x-1">
                              <button 
                                onClick={() => onEdit(workflow)}
                                className="p-1.5 text-outline hover:text-on-surface transition-colors"
                              >
                                <span className="material-symbols-outlined text-[16px]">edit</span>
                              </button>
                              <button 
                                onClick={() => handleDelete(workflow.id)}
                                className="p-1.5 text-outline hover:text-error transition-colors"
                              >
                                <span className="material-symbols-outlined text-[16px]">delete</span>
                              </button>
                            </div>
                          </div>

                          <div>
                            <h4 className="font-headline text-xl text-on-surface group-hover:text-primary transition-colors">
                              {workflow.display_name || workflow.name}
                            </h4>
                            <p className="font-mono text-[8px] text-outline uppercase tracking-wider opacity-60">
                              ID: {workflow.name}
                            </p>
                            <p className="font-body text-xs text-[#a38b88] mt-2 line-clamp-2 leading-relaxed">
                              {workflow.description || "No description provided for this autonomous protocol."}
                            </p>
                          </div>

                          <div className="pt-4 border-t border-outline-variant/5">
                            <p className="font-label text-[9px] text-outline uppercase tracking-widest mb-3">
                              Logic Nodes ({workflow.nodes.length})
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {workflow.node_order.slice(0, 4).map((nodeName, i) => (
                                <span key={i} className="px-2 py-1 bg-surface-container-high/50 text-[9px] font-mono text-tertiary border border-outline-variant/10">
                                  {nodeName}
                                </span>
                              ))}
                              {workflow.node_order.length > 4 && (
                                <span className="px-2 py-1 bg-surface-container-high/50 text-[9px] font-mono text-outline border border-outline-variant/10">
                                  +{workflow.node_order.length - 4} MORE
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="mt-8 flex justify-end relative z-10">
                          <button
                            onClick={() => handleExecute(workflow.id)}
                            disabled={executingId === workflow.id}
                            className={`w-full py-2.5 font-label text-[10px] uppercase tracking-[0.3em] transition-all flex items-center justify-center space-x-3 ${
                              executingId === workflow.id 
                                ? 'bg-secondary/20 text-secondary cursor-wait' 
                                : 'bg-surface-container-highest text-primary hover:bg-primary/20 border border-primary/10'
                            }`}
                          >
                            {executingId === workflow.id ? (
                              <>
                                <div className="w-3 h-3 border-2 border-secondary/30 border-t-secondary rounded-full animate-spin"></div>
                                <span>Dispatching...</span>
                              </>
                            ) : (
                              <>
                                <span className="material-symbols-outlined text-sm">play_arrow</span>
                                <span>Invoke SOP</span>
                              </>
                            )}
                          </button>
                        </div>

                        {/* Accent line on hover */}
                        <div className="absolute bottom-0 left-0 h-[2px] bg-primary w-0 group-hover:w-full transition-all duration-500"></div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              </div>
            ));
          })()}
        </div>
      )}
    </div>
  );
}

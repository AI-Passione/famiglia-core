import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { SOPManager } from './SOPManager';
import { SOPBuilder } from './SOPBuilder';
import { CategoryCreator } from './CategoryCreator';
import type { ActionLog, SOPWorkflow, GraphDefinition, Task } from '../types';
import { API_BASE } from '../config';

interface OperationsProps {
  graphs: GraphDefinition[];
  selectedGraph: GraphDefinition | null;
  setSelectedGraph: (graph: GraphDefinition | null) => void;
  initialTasks: Task[];
}

export function Operations({ graphs: _graphs, selectedGraph: _selectedGraph, setSelectedGraph: _setSelectedGraph, initialTasks: _initialTasks }: OperationsProps) {
  const [viewMode, setViewMode] = useState<'specific' | 'global'>('specific');
  const [opsMode, setOpsMode] = useState<'pipelines' | 'sop'>('pipelines');
  const [isCreatingSOP, setIsCreatingSOP] = useState(false);
  const [isCreatingCategory, setIsCreatingCategory] = useState(false);
  const [editingSOP, setEditingSOP] = useState<SOPWorkflow | null>(null);
  const [sopRefreshKey, setSopRefreshKey] = useState(0);

  // Agent Action Ledger State
  const [actions, setActions] = useState<ActionLog[]>([]);
  const [loadingActions, setLoadingActions] = useState(true);

  useEffect(() => {
    const fetchActions = async () => {
      try {
        const res = await fetch(`${API_BASE}/actions?limit=50`);
        if (res.ok) {
          const data = await res.json();
          // API returns { actions: ActionLog[], totalCount: number }
          setActions(data.actions || []);
        }
      } catch (err) {
        console.error("Error fetching actions:", err);
      } finally {
        setLoadingActions(false);
      }
    };
    fetchActions();
  }, []);

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="p-8 space-y-12"
    >
      {/* Tab Header */}
      <div className="flex items-center space-x-12 border-b border-outline-variant/10 pb-6">
        <button 
          onClick={() => setOpsMode('pipelines')}
          className={`font-headline text-2xl transition-all ${opsMode === 'pipelines' ? 'text-primary' : 'text-outline hover:text-on-surface'}`}
        >
          Operational Pipelines
        </button>
        <button 
          onClick={() => setOpsMode('sop')}
          className={`font-headline text-2xl transition-all ${opsMode === 'sop' ? 'text-primary' : 'text-outline hover:text-on-surface'}`}
        >
          SOP Hub
        </button>
      </div>

      <AnimatePresence mode="wait">
        {opsMode === 'pipelines' ? (
          <motion.div
            key="pipelines"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-12"
          >
            {/* Strategy & Governance Header */}
            <div className="flex justify-between items-end">
              <div>
                <h3 data-testid="mission-command-header" className="font-headline text-3xl text-on-surface">Mission Command & Tool Ledger</h3>
                <p className="font-label text-xs text-tertiary uppercase tracking-[0.4em] mt-2 opacity-60">
                  Autonomous Strategic Trajectory // 0xOPS
                </p>
              </div>

              <div className="flex glass-module p-1 border border-outline-variant/10">
                <button 
                  onClick={() => setViewMode('specific')}
                  className={`px-6 py-2 font-label text-[10px] uppercase tracking-widest transition-all ${viewMode === 'specific' ? 'bg-primary text-black' : 'text-outline hover:text-on-surface'}`}
                >
                  Specific View
                </button>
                <button 
                  onClick={() => setViewMode('global')}
                  className={`px-6 py-2 font-label text-[10px] uppercase tracking-widest transition-all ${viewMode === 'global' ? 'bg-primary text-black' : 'text-outline hover:text-on-surface'}`}
                >
                  Global Sync
                </button>
              </div>
            </div>

            {/* Main Content Areas */}
            <div className="grid grid-cols-12 gap-8">
              {/* Left Column: Mission Logs & Dialogue */}
              <div className="col-span-12 lg:col-span-7 space-y-12">
                {/* Agent Dialogue Section */}
                <section className="space-y-6">
                  <div className="flex items-center space-x-4">
                    <span className="material-symbols-outlined text-primary text-xl">forum</span>
                    <h4 data-testid="strategic-dialogue-header" className="font-label text-xs uppercase tracking-[0.3em] text-on-surface-variant">Strategic Dialogue</h4>
                    <div className="h-[1px] flex-1 bg-outline-variant/20"></div>
                  </div>
                  <div className="glass-module border border-outline-variant/10 p-6 h-[400px] flex items-center justify-center">
                    <p className="font-body text-outline italic opacity-50">Inter-agent negotiation logs initializing...</p>
                  </div>
                </section>

                {/* Mission Execution Logs */}
                <section className="space-y-6">
                  <div className="flex items-center space-x-4">
                    <span className="material-symbols-outlined text-primary text-xl">terminal</span>
                    <h4 data-testid="mission-logs-header" className="font-label text-xs uppercase tracking-[0.3em] text-on-surface-variant">Mission Execution Logs</h4>
                    <div className="h-[1px] flex-1 bg-outline-variant/20"></div>
                  </div>
                  <div className="glass-module border border-outline-variant/10 p-6 h-[300px] flex items-center justify-center">
                    <p className="font-body text-outline italic opacity-50">Central command stream pending connection...</p>
                  </div>
                </section>
              </div>

              {/* Right Column: Tool Action Ledger */}
              <div className="col-span-12 lg:col-span-5">
                <section className="space-y-6 flex flex-col h-full">
                  <div className="flex items-center space-x-4">
                    <span className="material-symbols-outlined text-primary text-xl">build</span>
                    <h4 data-testid="tool-ledger-header" className="font-label text-xs uppercase tracking-[0.3em] text-on-surface-variant">Tool Action Ledger</h4>
                    <div className="h-[1px] flex-1 bg-outline-variant/20"></div>
                  </div>
                  
                  <div className="glass-module border border-outline-variant/10 overflow-hidden flex-1 flex flex-col min-h-[700px]">
                    <div className="p-4 border-b border-outline-variant/10 bg-primary/5">
                      <p className="font-label text-[9px] uppercase tracking-widest text-primary flex items-center">
                        <span className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse mr-2"></span>
                        Real-time Intervention Stream
                      </p>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                      {loadingActions ? (
                        <div className="flex items-center justify-center h-full">
                          <div className="w-8 h-8 border-2 border-primary/20 border-t-primary rounded-full animate-spin"></div>
                        </div>
                      ) : actions.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full space-y-4 opacity-30">
                          <span className="material-symbols-outlined text-4xl">inventory_2</span>
                          <p className="font-label text-[10px] uppercase tracking-widest text-outline">No Tool Actions Recorded</p>
                        </div>
                      ) : Array.isArray(actions) ? (
                        actions.map((action, idx) => (
                          <motion.div
                            key={action.id}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: idx * 0.03 }}
                            className="p-4 bg-surface-container-highest/30 border-l-2 border-primary/40 hover:bg-surface-container-highest/50 transition-colors group"
                          >
                            <div className="flex justify-between items-start mb-2">
                              <p className="font-mono text-[10px] text-primary">{action.agent_name}</p>
                              <span className="font-mono text-[8px] text-outline opacity-50">
                                {new Date(action.timestamp).toLocaleTimeString()}
                              </span>
                            </div>
                            <h5 className="font-headline text-sm text-on-surface mb-1 group-hover:text-primary transition-colors">
                              {action.action_type}
                            </h5>
                            <div className="mt-2 p-2 bg-black/20 rounded font-mono text-[9px] text-outline leading-tight overflow-hidden text-ellipsis">
                              {action.action_details ? JSON.stringify(action.action_details).substring(0, 100) : 'No details available'}...
                            </div>
                          </motion.div>
                        ))
                      ) : null}
                    </div>
                  </div>
                </section>
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="sop"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <SOPManager 
              refreshKey={sopRefreshKey}
              onEdit={(wf) => setEditingSOP(wf)} 
              onCreate={(mode) => {
                if (mode === 'category') {
                  setIsCreatingCategory(true);
                } else {
                  setIsCreatingSOP(true);
                }
              }} 
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Persistence Modals */}
      <AnimatePresence>
        {(isCreatingSOP || editingSOP) && (
          <SOPBuilder
            workflow={editingSOP}
            onClose={() => {
              setIsCreatingSOP(false);
              setEditingSOP(null);
              setSopRefreshKey(prev => prev + 1);
            }}
            onSave={() => {
              setSopRefreshKey(prev => prev + 1);
            }}
          />
        )}

        {isCreatingCategory && (
          <CategoryCreator
            onClose={() => setIsCreatingCategory(false)}
            onSave={() => setSopRefreshKey(prev => prev + 1)}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}

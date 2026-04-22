import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { SOPManager } from './SOPManager';
import { SOPBuilder } from './SOPBuilder';
import { CategoryCreator } from './CategoryCreator';
import type { ActionLog, SOPWorkflow } from '../types';
import { API_BASE } from '../config';


interface MissionLog {
  id: string;
  graph_id: string;
  timestamp: string;
  status: 'success' | 'failure' | 'running' | 'pending' | 'queued';
  duration: string;
  initiator: string;
}

interface Conversation {
  id: number;
  conversation_key: string;
  updated_at: string;
  latest_message: string;
  latest_agent: string;
}

export function Operations() {
  const navigate = useNavigate();
  const [opsMode, setOpsMode] = useState<'pipelines' | 'sop'>('pipelines');

  const [isCreatingSOP, setIsCreatingSOP] = useState(false);
  const [isCreatingCategory, setIsCreatingCategory] = useState(false);
  const [editingSOP, setEditingSOP] = useState<SOPWorkflow | null>(null);
  const [sopRefreshKey, setSopRefreshKey] = useState(0);

  // Dashboard Feeds State
  const [actions, setActions] = useState<ActionLog[]>([]);
  const [missionLogs, setMissionLogs] = useState<MissionLog[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      const [actionsRes, logsRes, convsRes] = await Promise.all([
        fetch(`${API_BASE}/actions?limit=50`),
        fetch(`${API_BASE}/operations/mission-logs/all`),
        fetch(`${API_BASE}/chat/conversations`)
      ]);

      if (actionsRes.ok) {
        const data = await actionsRes.json();
        setActions(data.actions || []);
      }
      if (logsRes.ok) {
        const data = await logsRes.json();
        setMissionLogs(data || []);
      }
      if (convsRes.ok) {
        const data = await convsRes.json();
        setConversations(data || []);
      }
    } catch (err) {
      console.error("Error fetching dashboard SITREP:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    // Auto-refresh every 30 seconds as requested by the Don
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="p-8 space-y-12"
    >
      {/* Tab Header - Premium Navigation */}
      <div className="flex items-center space-x-4 border-b border-outline-variant/10 pb-6">
        <button 
          onClick={() => setOpsMode('pipelines')}
          className={`relative px-8 py-3 rounded-xl font-headline text-xl transition-all flex items-center space-x-3 group ${
            opsMode === 'pipelines' ? 'text-primary' : 'text-outline hover:text-on-surface hover:bg-white/[0.03]'
          }`}
        >
          <span className={`material-symbols-outlined transition-transform duration-300 ${opsMode === 'pipelines' ? 'scale-110' : 'opacity-40 group-hover:opacity-100 group-hover:rotate-12'}`}>
            account_tree
          </span>
          <span>Operational Pipelines</span>
          {opsMode === 'pipelines' && (
            <motion.div 
              layoutId="activeTab"
              className="absolute bottom-[-24px] left-8 right-8 h-[2px] bg-primary shadow-[0_0_15px_rgba(99,102,241,0.5)]"
              transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
            />
          )}
        </button>

        <button 
          onClick={() => setOpsMode('sop')}
          className={`relative px-8 py-3 rounded-xl font-headline text-xl transition-all flex items-center space-x-3 group ${
            opsMode === 'sop' ? 'text-primary' : 'text-outline hover:text-on-surface hover:bg-white/[0.03]'
          }`}
        >
          <span className={`material-symbols-outlined transition-transform duration-300 ${opsMode === 'sop' ? 'scale-110' : 'opacity-40 group-hover:opacity-100 group-hover:-rotate-12'}`}>
            auto_stories
          </span>
          <span>SOP Hub</span>
          {opsMode === 'sop' && (
            <motion.div 
              layoutId="activeTab"
              className="absolute bottom-[-24px] left-8 right-8 h-[2px] bg-primary shadow-[0_0_15px_rgba(99,102,241,0.5)]"
              transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
            />
          )}
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
            </div>

            {/* Main Content Areas */}
            <div className="grid grid-cols-12 gap-8">
              {/* Left Column: Mission Logs & Dialogue */}
              <div className="col-span-12 lg:col-span-7 space-y-12">
                {/* Mission Execution Logs */}
                <section className="space-y-6">
                  <div className="flex items-center space-x-4">
                    <span className="material-symbols-outlined text-primary text-xl">terminal</span>
                    <h4 data-testid="mission-logs-header" className="font-label text-xs uppercase tracking-[0.3em] text-on-surface-variant">Mission Execution Logs</h4>
                    <div className="h-[1px] flex-1 bg-outline-variant/20"></div>
                  </div>
                  
                  <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                    {loading ? (
                      <div className="glass-module border border-outline-variant/10 p-6 flex justify-center">
                        <div className="w-6 h-6 border-2 border-primary/20 border-t-primary rounded-full animate-spin"></div>
                      </div>
                    ) : missionLogs.length === 0 ? (
                      <div className="glass-module border border-outline-variant/10 p-6 flex items-center justify-center">
                        <p className="font-body text-outline italic opacity-50 text-sm">No mission execution history found...</p>
                      </div>
                    ) : (
                      missionLogs.map((log) => (
                        <motion.div
                          key={log.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          onClick={() => navigate(`/operations/tasks/${log.id}`)}
                          className="glass-module border border-outline-variant/10 p-4 hover:border-primary/30 transition-all group cursor-pointer"
                        >
                          <div className="flex justify-between items-start">
                            <div className="space-y-1">
                              <div className="flex items-center space-x-3">
                                <span className="font-mono text-[10px] text-primary">{log.id}</span>
                                <span className={`px-2 py-0.5 rounded-full font-label text-[8px] uppercase tracking-widest ${
                                  log.status === 'success' ? 'bg-success/10 text-success' :
                                  log.status === 'running' ? 'bg-primary/10 text-primary animate-pulse' :
                                  (log.status === 'pending' || log.status === 'queued') ? 'bg-amber-500/10 text-amber-500' :
                                  'bg-error/10 text-error'
                                }`}>
                                  {log.status}
                                </span>
                              </div>
                              <h5 className="font-headline text-on-surface group-hover:text-primary transition-colors">{log.graph_id}</h5>
                            </div>
                            <div className="text-right">
                              <p className="font-mono text-[9px] text-outline opacity-60">{log.timestamp}</p>
                              <p className="font-label text-[8px] uppercase tracking-tighter text-outline-variant mt-1">Duration: {log.duration}</p>
                            </div>
                          </div>
                          <div className="mt-3 flex items-center justify-between border-t border-outline-variant/5 pt-3">
                            <span className="font-label text-[9px] text-outline/50 uppercase tracking-widest">Initiator: {log.initiator}</span>
                            <span className="material-symbols-outlined text-sm text-outline opacity-40 group-hover:opacity-100 transition-opacity">arrow_forward</span>
                          </div>
                        </motion.div>
                      ))
                    )}
                  </div>
                </section>

                {/* Agent Dialogue Section */}
                <section className="space-y-6">
                  <div className="flex items-center space-x-4">
                    <span className="material-symbols-outlined text-primary text-xl">forum</span>
                    <h4 data-testid="strategic-dialogue-header" className="font-label text-xs uppercase tracking-[0.3em] text-on-surface-variant">Strategic Dialogue</h4>
                    <div className="h-[1px] flex-1 bg-outline-variant/20"></div>
                  </div>
                  
                  <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                    {loading ? (
                      <div className="glass-module border border-outline-variant/10 p-6 flex justify-center">
                        <div className="w-6 h-6 border-2 border-primary/20 border-t-primary rounded-full animate-spin"></div>
                      </div>
                    ) : conversations.length === 0 ? (
                      <div className="glass-module border border-outline-variant/10 p-6 flex items-center justify-center">
                        <p className="font-body text-outline italic opacity-50 text-sm">Inter-agent negotiation logs pending...</p>
                      </div>
                    ) : (
                      conversations.map((conv) => (
                        <motion.div
                          key={conv.id}
                          initial={{ opacity: 0, scale: 0.98 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className="glass-module border border-outline-variant/10 p-4 hover:bg-white/[0.02] transition-all cursor-pointer relative overflow-hidden"
                        >
                          <div className="absolute top-0 right-0 p-2 opacity-20">
                            <span className="material-symbols-outlined text-xs">history</span>
                          </div>
                          <div className="flex justify-between items-center mb-2">
                            <div className="flex items-center space-x-2">
                              <span className="w-1.5 h-1.5 bg-primary rounded-full"></span>
                              <p className="font-label text-[10px] text-primary uppercase tracking-widest">{conv.latest_agent || 'Unknown Agent'}</p>
                            </div>
                            <span className="font-mono text-[8px] text-outline-variant">
                              {new Date(conv.updated_at).toLocaleTimeString()}
                            </span>
                          </div>
                          <p className="font-body text-xs text-on-surface-variant line-clamp-2 leading-relaxed italic">
                            "{conv.latest_message || 'No messages recorded'}"
                          </p>
                          <div className="mt-2 flex items-center space-x-2 opacity-40">
                            <span className="font-mono text-[8px] uppercase tracking-tighter">Ref: {conv.conversation_key.split(':').pop()}</span>
                          </div>
                        </motion.div>
                      ))
                    )}
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
                      {loading ? (
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

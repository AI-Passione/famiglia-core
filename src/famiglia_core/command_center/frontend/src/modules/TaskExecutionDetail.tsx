import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import type { TaskExecutionDetail as DetailType, TaskMessage, TaskNotification } from '../types';
import { API_BASE } from '../config';

export function TaskExecutionDetail() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<DetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = async () => {
    if (!taskId) return;
    try {
      const id = taskId.startsWith('ML-') ? parseInt(taskId.replace('ML-', '')) : parseInt(taskId);
      const res = await fetch(`${API_BASE}/operations/mission-logs/detail/${id}`);
      if (res.ok) {
        const data = await res.json();
        setDetail(data);
      } else {
        setError("Mission dossier not found in archives.");
      }
    } catch (err) {
      console.error("Error fetching task SITREP:", err);
      setError("Failed to establish secure link to mission data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
    const interval = setInterval(fetchDetail, 10000); // Polling for live updates
    return () => clearInterval(interval);
  }, [taskId]);

  // Combine and sort events for the timeline
  const timelineEvents = useMemo(() => {
    if (!detail) return [];
    const events: Array<{
      type: 'message' | 'notification';
      timestamp: string;
      data: any;
    }> = [];

    detail.messages.forEach(m => events.push({ type: 'message', timestamp: m.created_at, data: m }));
    detail.notifications.forEach(n => events.push({ type: 'notification', timestamp: n.created_at, data: n }));

    return events.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [detail]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-40">
        <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="flex flex-col items-center justify-center py-40 space-y-6">
        <span className="material-symbols-outlined text-error text-6xl">warning</span>
        <h2 className="font-headline text-2xl text-on-surface uppercase tracking-[0.2em]">{error || "Access Denied"}</h2>
        <button 
          onClick={() => navigate('/operations')}
          className="px-6 py-2 border border-outline-variant/30 rounded-lg font-label text-xs uppercase tracking-widest hover:bg-white/5 transition-all"
        >
          Return to Operations
        </button>
      </div>
    );
  }

  const { task } = detail;
  const statusTone = 
    task.status === 'completed' ? 'emerald' : 
    task.status === 'failed' ? 'rose' : 
    task.status === 'in_progress' ? 'indigo' : 'slate';

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8"
    >
      {/* Header SITREP */}
      <div className="flex justify-between items-start">
        <div className="space-y-2">
          <button 
            onClick={() => navigate('/operations')}
            className="flex items-center space-x-2 text-outline hover:text-primary transition-colors mb-4 group"
          >
            <span className="material-symbols-outlined text-sm group-hover:-translate-x-1 transition-transform">arrow_back</span>
            <span className="font-label text-[10px] uppercase tracking-[0.2em]">Operations Command</span>
          </button>
          <div className="flex items-center space-x-4">
            <h1 className="font-headline text-4xl text-on-surface">Mission ML-{task.id.toString().padStart(3, '0')}</h1>
            <span className={`px-4 py-1 rounded-full font-label text-[10px] uppercase tracking-[0.3em] bg-${statusTone}-500/10 text-${statusTone}-400 border border-${statusTone}-500/20`}>
              {task.status}
            </span>
          </div>
          <p className="font-label text-xs text-outline tracking-widest uppercase opacity-60">
            {task.title} // Assigned to: <span className="text-primary">{task.assigned_agent || task.expected_agent || 'Unassigned'}</span>
          </p>
        </div>

        <div className="flex flex-col items-end space-y-4">
           <div className="glass-module border border-outline-variant/10 p-4 min-w-[200px]">
              <p className="font-label text-[9px] text-outline uppercase tracking-widest mb-1">Created At</p>
              <p className="font-mono text-xs text-on-surface">{new Date(task.created_at).toLocaleString()}</p>
              {task.completed_at && (
                <>
                  <p className="font-label text-[9px] text-outline uppercase tracking-widest mt-3 mb-1">Completed At</p>
                  <p className="font-mono text-xs text-on-surface">{new Date(task.completed_at).toLocaleString()}</p>
                </>
              )}
           </div>
        </div>
      </div>

      {/* Main Intel Grid */}
      <div className="grid grid-cols-12 gap-8">
        {/* Left: Mission Specs & Summary */}
        <div className="col-span-12 lg:col-span-4 space-y-8">
          <section className="glass-module border border-outline-variant/10 overflow-hidden">
            <div className="p-4 bg-primary/5 border-b border-outline-variant/10">
              <h3 className="font-label text-[10px] uppercase tracking-[0.3em] text-primary">Mission Payload</h3>
            </div>
            <div className="p-6 space-y-6">
              <div className="p-4 bg-black/20 rounded-xl border border-outline-variant/5">
                <p className="font-body text-sm text-on-surface-variant leading-relaxed whitespace-pre-wrap italic opacity-80">
                  {task.task_payload}
                </p>
              </div>
              
              {task.result_summary && (
                <div className="space-y-3">
                  <h4 className="font-label text-[9px] uppercase tracking-widest text-outline-variant">Debrief Summary</h4>
                  <div className="p-4 bg-emerald-500/5 rounded-xl border border-emerald-500/20">
                    <p className="font-body text-sm text-emerald-100/80 leading-relaxed">
                      {task.result_summary}
                    </p>
                  </div>
                </div>
              )}

              {task.error_details && (
                <div className="space-y-3">
                  <h4 className="font-label text-[9px] uppercase tracking-widest text-rose-400">Critical Error Logs</h4>
                  <div className="p-4 bg-rose-500/5 rounded-xl border border-rose-500/20">
                    <p className="font-mono text-xs text-rose-200/80 leading-relaxed whitespace-pre-wrap">
                      {task.error_details}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </section>

          <section className="glass-module border border-outline-variant/10 p-6 space-y-4">
            <h3 className="font-label text-[10px] uppercase tracking-[0.3em] text-on-surface-variant border-b border-outline-variant/10 pb-4">Metadata Context</h3>
            <div className="space-y-4">
               {Object.entries(task.metadata || {}).map(([key, value]) => (
                 <div key={key} className="flex justify-between items-center text-[11px]">
                   <span className="font-mono text-outline uppercase">{key}</span>
                   <span className="font-mono text-on-surface text-right max-w-[150px] truncate">{JSON.stringify(value)}</span>
                 </div>
               ))}
            </div>
          </section>
        </div>

        {/* Right: Operational Timeline (The "Under the Hood" part) */}
        <div className="col-span-12 lg:col-span-8 space-y-6">
          <div className="flex items-center space-x-4">
            <span className="material-symbols-outlined text-primary">analytics</span>
            <h3 className="font-headline text-xl text-on-surface">Execution Timeline</h3>
            <div className="h-[1px] flex-1 bg-outline-variant/20"></div>
          </div>

          <div className="space-y-6 relative before:absolute before:left-[19px] before:top-2 before:bottom-2 before:w-[1px] before:bg-outline-variant/20">
            {timelineEvents.length === 0 ? (
              <div className="py-20 text-center opacity-30">
                <span className="material-symbols-outlined text-4xl mb-2">history</span>
                <p className="font-label text-[10px] uppercase tracking-widest">No internal activity logs recorded...</p>
              </div>
            ) : (
              timelineEvents.map((event, idx) => (
                <motion.div 
                  key={`${event.type}-${idx}`}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="relative pl-12"
                >
                  {/* Timeline Dot */}
                  <div className={`absolute left-0 top-1 w-10 h-10 flex items-center justify-center z-10`}>
                    <div className={`w-2.5 h-2.5 rounded-full border-2 border-background shadow-[0_0_10px_rgba(0,0,0,0.5)] ${
                      event.type === 'notification' ? 'bg-primary shadow-[0_0_8px_rgba(99,102,241,0.5)]' : 'bg-on-surface-variant'
                    }`}></div>
                  </div>

                  {/* Content Card */}
                  <div className={`glass-module border border-outline-variant/10 p-5 hover:bg-white/[0.02] transition-all group relative overflow-hidden`}>
                    {/* Status accent for notifications */}
                    {event.type === 'notification' && (
                      <div className={`absolute left-0 top-0 bottom-0 w-[2px] ${
                        event.data.type === 'success' ? 'bg-emerald-500' :
                        event.data.type === 'error' ? 'bg-rose-500' :
                        event.data.type === 'warning' ? 'bg-amber-500' : 'bg-primary'
                      }`}></div>
                    )}

                    <div className="flex justify-between items-start mb-3">
                      <div className="flex items-center space-x-3">
                        <span className={`material-symbols-outlined text-sm ${event.type === 'notification' ? 'text-primary' : 'text-outline'}`}>
                          {event.type === 'notification' ? 'notifications' : 'chat_bubble'}
                        </span>
                        <p className="font-label text-[10px] uppercase tracking-widest text-on-surface">
                          {event.type === 'notification' ? (event.data.agent_name || 'System') : event.data.sender}
                        </p>
                        {event.type === 'message' && (
                          <span className="font-mono text-[8px] text-outline px-1.5 py-0.5 rounded bg-white/5">
                            {event.data.role}
                          </span>
                        )}
                      </div>
                      <span className="font-mono text-[9px] text-outline opacity-50">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                    </div>

                    <div className="space-y-3">
                      {event.type === 'notification' && (
                        <p className="font-headline text-sm text-on-surface">{event.data.title}</p>
                      )}
                      <p className={`font-body text-xs leading-relaxed ${
                        event.type === 'message' ? 'text-on-surface-variant italic border-l border-primary/20 pl-3' : 'text-on-surface'
                      }`}>
                        {event.type === 'notification' ? event.data.message : event.data.content}
                      </p>
                    </div>

                    {/* Meta/Tool Details if any */}
                    {event.data.metadata && Object.keys(event.data.metadata).length > 0 && (
                      <div className="mt-4 pt-3 border-t border-outline-variant/5">
                         <div className="flex flex-wrap gap-2">
                            {Object.entries(event.data.metadata).map(([k, v]) => (
                              k !== 'task_id' && (
                                <span key={k} className="font-mono text-[8px] text-outline-variant bg-black/30 px-2 py-0.5 rounded">
                                  {k}: {typeof v === 'string' ? v : JSON.stringify(v)}
                                </span>
                              )
                            ))}
                         </div>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Task } from '../../types';
import { API_BASE } from '../../config';

interface PulseStatProps {
  value: string;
  label: string;
  color: string;
}

function PulseStat({ value, label, color }: PulseStatProps) {
  const colorClass = color === 'tertiary' ? 'text-tertiary' : color === 'primary' ? 'text-primary' : 'text-red-400';
  return (
    <div className="text-center">
      <p className={`font-label ${colorClass} text-4xl font-bold tracking-tighter`}>{value}</p>
      <p className="font-label text-outline text-[10px] uppercase tracking-widest mt-1">{label}</p>
    </div>
  );
}

interface MissionUpdate {
  graph_id: string;
  timestamp: string;
  status: string;
  initiator: string;
}

// Map orchestration graph IDs to readable labels
const GRAPH_LABELS: Record<string, string> = {
  market_research:      'Market Research',
  deep_dive_analysis:   'Deep Dive Analysis',
  simple_data_analysis: 'Data Analysis',
  data_ingestion:       'Data Ingestion',
  prd_drafting:         'PRD Drafting',
  prd_review:           'PRD Review',
  grooming:             'Grooming',
  code_implementation:  'Code Implementation',
  milestone_creation:   'Milestone Creation',
};

// Agent → domain for the "Last Update" label
const INITIATOR_DOMAIN: Record<string, string> = {
  rossini:  'Intelligence',
  kowalski: 'Analytics',
  riccardo: 'Engineering',
  alfredo:  'Command',
  bella:    'Administration',
  vito:     'Secure Comms',
};

interface OpsPulseProps {
  completedTasks: number;
  scheduledTasks: number;
  failedTasks: number;
  tasks: Task[];
}

export function OpsPulse({ completedTasks, scheduledTasks, failedTasks, tasks }: OpsPulseProps) {
  const [updates, setUpdates] = useState<MissionUpdate[]>([]);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch(`${API_BASE}/operations/mission-logs/all`);
        if (res.ok) {
          const data = await res.json();
          const logs: MissionUpdate[] = Array.isArray(data) ? data : [];
          // Dedupe: keep only the latest log per graph_id
          const seen = new Set<string>();
          const latest: MissionUpdate[] = [];
          for (const log of logs) {
            if (!seen.has(log.graph_id)) {
              seen.add(log.graph_id);
              latest.push(log);
            }
          }
          setUpdates(latest.slice(0, 3));
        }
      } catch (e) {
        // silently fail — update cards will just be hidden
      }
    };
    fetchLogs();
    const interval = setInterval(fetchLogs, 30000);
    return () => clearInterval(interval);
  }, []);

  // Recent non-pending tasks for Mission Outcomes
  const recentTasks = (tasks || [])
    .filter(t => t && t.status !== 'pending')
    .slice(0, 4);

  const BORDER_COLORS = ['#ffb3b5', '#a8d8b0', '#b3c6ff'];

  return (
    <div className="bg-surface-container-low p-8 relative overflow-hidden rounded-2xl border border-outline/5">
      {/* Heartbeat Title */}
      <div className="flex items-center gap-3 mb-8">
        <h3 className="font-headline text-2xl text-on-surface">Pulse</h3>
        <span className="relative flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-60"></span>
          <span className="relative inline-flex rounded-full h-3 w-3 bg-primary"></span>
        </span>
        <span className="font-label text-[10px] text-outline tracking-widest uppercase ml-auto">Live Telemetry</span>
      </div>

      {/* BANs */}
      <div className="grid grid-cols-3 gap-8 pb-8 border-b border-outline/10">
        <PulseStat value={completedTasks.toString().padStart(2, '0')} label="Tasks Carried Out" color="tertiary" />
        <PulseStat value={scheduledTasks.toString().padStart(2, '0')} label="Tasks Scheduled" color="primary" />
        <PulseStat value={failedTasks.toString().padStart(2, '0')} label="Tasks Failed" color="on-surface" />
      </div>

      {/* Mission Outcomes */}
      <div className="py-6 border-b border-outline/10">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-headline text-base text-on-surface">Mission Outcomes</h4>
          <span className="font-label text-[9px] uppercase tracking-widest text-outline bg-surface-container px-2 py-1 rounded-sm">Recent 24h</span>
        </div>
        <div className="space-y-3 max-h-[220px] overflow-y-auto custom-scrollbar pr-1">
          {recentTasks.length > 0 ? (
            recentTasks.map((task, idx) => {
              const isSuccess = task.status === 'completed' || task.status === 'success';
              const isFailed = task.status === 'failed' || task.status === 'error';
              const colorClass = isSuccess ? 'text-primary' : isFailed ? 'text-red-400' : 'text-tertiary';
              const bgClass = isSuccess ? 'bg-primary/10 border-primary/20' : isFailed ? 'bg-red-500/10 border-red-500/20' : 'bg-surface-container-highest/30 border-outline/10';
              const icon = isSuccess ? 'check_circle' : isFailed ? 'cancel' : 'pending';
              return (
                <motion.div
                  key={task.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.07 }}
                  className={`p-3 border rounded-xl flex gap-3 items-start ${bgClass}`}
                >
                  <span className={`material-symbols-outlined ${colorClass} text-[18px] mt-0.5 shrink-0`}>{icon}</span>
                  <div className="min-w-0">
                    <h5 className="font-headline text-sm text-on-surface leading-tight line-clamp-1">{task.title}</h5>
                    <p className="font-body text-[11px] text-on-surface-variant italic line-clamp-1 mt-0.5">
                      {task.result_summary || task.task_payload || '—'}
                    </p>
                  </div>
                  <span className={`font-label text-[9px] uppercase tracking-widest ml-auto shrink-0 ${colorClass}`}>
                    {task.status ? task.status.replace('_', ' ') : '—'}
                  </span>
                </motion.div>
              );
            })
          ) : (
            <p className="font-label text-xs text-outline text-center py-4">No recent outcomes</p>
          )}
        </div>
      </div>

      {/* Live Update Cards from Graph Mission Logs */}
      <AnimatePresence>
        {updates.length > 0 && (
          <div className="mt-6 flex gap-3">
            {updates.map((update, idx) => (
              <motion.div
                key={update.graph_id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="flex-1 bg-surface-container-highest/20 p-4 border-l-2 rounded-r-xl"
                style={{ borderColor: BORDER_COLORS[idx % BORDER_COLORS.length] }}
              >
                <p className="font-label text-[10px] text-outline uppercase tracking-widest mb-1">
                  Last Update: {INITIATOR_DOMAIN[update.initiator?.toLowerCase()] || update.initiator || 'Agent'}
                </p>
                <p className="font-headline text-sm text-on-surface line-clamp-1">
                  {GRAPH_LABELS[update.graph_id] || update.graph_id.replace(/_/g, ' ')}
                </p>
                <p className="font-label text-[9px] text-outline mt-1 uppercase tracking-widest">
                  {new Date(update.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  {' · '}
                  <span className={update.status === 'success' || update.status === 'completed' ? 'text-primary' : 'text-red-400'}>
                    {update.status}
                  </span>
                </p>
              </motion.div>
            ))}
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

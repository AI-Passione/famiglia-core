import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import type { Task } from '../../types';

// ─── Heartbeat SVG (ECG / hospital-monitor style) ───────────────────────────
function HeartbeatLine() {
  const path = "M0,16 L28,16 L34,16 L38,4 L42,28 L46,8 L50,16 L56,16 L120,16";
  return (
    <div className="relative w-16 h-6 flex items-center">
      <svg
        viewBox="0 0 120 32"
        className="w-full h-full text-primary overflow-visible"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <style>{`
          @keyframes scan {
            0% { clip-path: inset(0 100% 0 0); }
            50% { clip-path: inset(0 0 0 0); }
            100% { clip-path: inset(0 0 0 100%); }
          }
          .ecg-path {
            animation: scan 2s linear infinite;
            filter: drop-shadow(0 0 4px rgba(255, 179, 181, 0.4));
          }
        `}</style>
        <path
          className="ecg-path"
          d={path}
        />
        {/* Moving glow head - inside SVG for perfect coordinate alignment */}
        <motion.circle
          r="2.5"
          fill="currentColor"
          className="shadow-[0_0_8px_#ffb3b5]"
          style={{ offsetPath: `path('${path}')` }}
          animate={{ 
            offsetDistance: ["0%", "100%"],
            opacity: [0, 1, 1, 0]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "linear",
            times: [0, 0.1, 0.9, 1]
          }}
        />
      </svg>
    </div>
  );
}

// ─── Feature graph IDs (orchestration features only) ─────────────────────────
const FEATURE_GRAPH_IDS = new Set([
  'market_research',
  'deep_dive_analysis',
  'simple_data_analysis',
  'data_ingestion',
  'prd_drafting',
  'prd_review',
  'grooming',
  'code_implementation',
  'milestone_creation',
]);


// Map graph_id → Intelligence item_type for deep-link filter
const GRAPH_TO_ITEM_TYPE: Record<string, string> = {
  market_research:      'market_research',
  deep_dive_analysis:   'market_research',
  simple_data_analysis: 'analysis',
  data_ingestion:       'analysis',
  prd_drafting:         'prd',
  prd_review:           'prd',
  grooming:             'project',
  code_implementation:  'project',
  milestone_creation:   'project',
};

interface PulseStatProps {
  value: string;
  label: string;
  color: 'tertiary' | 'primary' | 'red';
}

function PulseStat({ value, label, color }: PulseStatProps) {
  const colorClass =
    color === 'tertiary' ? 'text-tertiary' :
    color === 'primary'  ? 'text-primary'  :
    'text-red-400';
  return (
    <div className="text-center">
      <p className={`font-label ${colorClass} text-4xl font-bold tracking-tighter`}>{value}</p>
      <p className="font-label text-outline text-[10px] uppercase tracking-widest mt-1">{label}</p>
    </div>
  );
}

// ─── Component Props ─────────────────────────────────────────────────────────
interface OpsPulseProps {
  completedTasks: number;
  scheduledTasks: number;
  failedTasks: number;
  tasks: Task[];
}

export function OpsPulse({ completedTasks, scheduledTasks, failedTasks, tasks }: OpsPulseProps) {
  const navigate = useNavigate();
  // Filter to feature-graph tasks only — greetings & generic tasks are excluded
  // Tasks triggered by graphs carry metadata.graph_id; fall back to title keyword match
  const featureTasks = (tasks || [])
    .filter(t => {
      if (!t) return false;
      
      const title = (t.title || '').toLowerCase();
      const payload = (t.task_payload || '').toLowerCase();
      
      // Explicitly exclude greetings
      if (title.includes('greeting') || title.includes('welcome') || payload.includes('greeting')) {
        return false;
      }

      const gid = (t.metadata as any)?.graph_id as string | undefined;
      if (gid && FEATURE_GRAPH_IDS.has(gid)) return true;
      
      // Keyword heuristic for tasks without metadata
      return (
        title.includes('market research') ||
        title.includes('research') ||
        title.includes('analysis') ||
        title.includes('prd') ||
        title.includes('grooming') ||
        title.includes('data ingestion') ||
        title.includes('milestone') ||
        title.includes('implementation')
      );
    })
    .slice(0, 5);

  const handleViewIntel = (task: Task) => {
    const gid = (task.metadata as any)?.graph_id as string | undefined;
    const itemType = (gid && GRAPH_TO_ITEM_TYPE[gid]) || 'market_research';
    window.open(`/intelligence.html?filter=${itemType}`, '_blank');
  };

  return (
    <div className="bg-surface-container-low p-8 relative overflow-hidden rounded-2xl border border-outline/5">

      {/* ── Title + ECG heartbeat ── */}
      <div className="flex items-center gap-3 mb-8">
        <h3 className="font-headline text-2xl text-on-surface">Pulse</h3>
        <HeartbeatLine />
        <span className="font-label text-[10px] text-outline tracking-widest uppercase ml-auto">Live Telemetry</span>
      </div>

      {/* ── BANs ── */}
      <div className="grid grid-cols-3 gap-8 pb-8 border-b border-outline/10">
        <PulseStat value={completedTasks.toString().padStart(2, '0')} label="Tasks Carried Out" color="tertiary" />
        <PulseStat value={scheduledTasks.toString().padStart(2, '0')} label="Tasks Scheduled"   color="primary" />
        <PulseStat value={failedTasks.toString().padStart(2, '0')}    label="Tasks Failed"       color="red" />
      </div>

      {/* ── Mission Outcomes (feature graphs only) ── */}
      <div className="pt-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-headline text-base text-on-surface">Mission Outcomes</h4>
          <span className="font-label text-[9px] uppercase tracking-widest text-outline bg-surface-container px-2 py-1 rounded-sm">
            Feature Graphs Only
          </span>
        </div>

        <div className="space-y-3 max-h-[300px] overflow-y-auto custom-scrollbar pr-1">
          {featureTasks.length > 0 ? (
            featureTasks.map((task, idx) => {
              const isSuccess = task.status === 'completed' || task.status === 'success';
              const isFailed  = task.status === 'failed'    || task.status === 'error';
              const isPending = task.status === 'pending'   || task.status === 'queued';
              
              const colorClass = isSuccess ? 'text-primary' : isFailed ? 'text-red-400' : isPending ? 'text-amber-500' : 'text-tertiary';
              const bgClass    = isSuccess
                ? 'bg-primary/10 border-primary/20'
                : isFailed
                  ? 'bg-red-500/10 border-red-500/20'
                  : isPending
                    ? 'bg-amber-500/10 border-amber-500/20'
                    : 'bg-surface-container-highest/30 border-outline/10';
              const icon = isSuccess ? 'check_circle' : isFailed ? 'cancel' : isPending ? 'schedule' : 'pending';

              const gid   = (task.metadata as any)?.graph_id as string | undefined;
              const isDoc = gid && (
                gid.includes('research') ||
                gid.includes('analysis') ||
                gid.includes('prd') ||
                gid.includes('grooming') ||
                gid.includes('implementation') ||
                gid.includes('milestone')
              );

              return (
                <motion.div
                  key={task.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.07 }}
                  onClick={() => navigate(`/operations/tasks/${task.id}`)}
                  title="View Detailed Execution Dossier"
                  className={`p-3 border rounded-xl flex gap-3 items-start ${bgClass} cursor-pointer hover:bg-surface-container-highest/60 transition-all active:scale-[0.98] group/card`}
                >
                  <span className={`material-symbols-outlined ${colorClass} text-[18px] mt-0.5 shrink-0`}>{icon}</span>

                  <div className="flex-1 min-w-0">
                    <h5 className="font-headline text-sm text-on-surface leading-tight line-clamp-1 group-hover/card:text-primary transition-colors">{task.title}</h5>
                    <p className="font-body text-[11px] text-on-surface-variant italic line-clamp-1 mt-0.5">
                      {task.result_summary || task.task_payload || '—'}
                    </p>
                  </div>

                  {/* ── Link to Intelligence page for doc-generating graphs ── */}
                  {(isSuccess && (isDoc || true)) && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleViewIntel(task);
                      }}
                      title="View in Intelligence"
                      className="shrink-0 mt-0.5 p-1.5 rounded-lg bg-primary/10 hover:bg-primary/25 text-primary transition-all group/link"
                    >
                      <span className="material-symbols-outlined text-[15px] group-hover/link:translate-x-0.5 transition-transform">
                        open_in_new
                      </span>
                    </button>
                  )}

                  <span className={`font-label text-[9px] uppercase tracking-widest shrink-0 self-center ${colorClass}`}>
                    {task.status ? task.status.replace('_', ' ') : '—'}
                  </span>
                </motion.div>
              );
            })
          ) : (
            <p className="font-label text-xs text-outline text-center py-6">No feature graph outcomes yet</p>
          )}
        </div>
      </div>

    </div>
  );
}

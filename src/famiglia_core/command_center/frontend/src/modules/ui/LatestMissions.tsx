import { motion } from 'framer-motion';
import type { Task } from '../../types';

interface LatestMissionsProps {
  tasks: Task[];
}

export function LatestMissions({ tasks }: LatestMissionsProps) {
  // Filter for tasks that are not pending, mostly completed/failed/in_progress but recently updated
  const recentTasks = (tasks || [])
    .filter(t => t && t.status !== 'pending')
    .slice(0, 4);

  return (
    <div className="bg-surface-container-low p-6 h-full flex flex-col relative overflow-hidden group">
      <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
        <span className="material-symbols-outlined text-[64px]">history_edu</span>
      </div>
      <div className="flex items-center justify-between mb-6 relative z-10">
        <h3 className="font-headline text-xl text-on-surface">Mission Outcomes</h3>
        <span className="font-label text-[10px] uppercase tracking-widest text-outline bg-surface-container px-2 py-1 rounded-sm">Recent 24h</span>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto custom-scrollbar relative z-10 pr-2">
        {recentTasks.length > 0 ? (
          recentTasks.map((task, idx) => {
            const isSuccess = task.status === 'completed' || task.status === 'success';
            const isFailed = task.status === 'failed' || task.status === 'error';
            // Determine colors and icons based on status
            const colorClass = isSuccess ? 'text-primary' : isFailed ? 'text-red-500' : 'text-tertiary';
            const bgClass = isSuccess ? 'bg-primary/10 border-primary/20' : isFailed ? 'bg-red-500/10 border-red-500/20' : 'bg-surface-container-highest/30 border-outline/10';
            const icon = isSuccess ? 'check_circle' : isFailed ? 'cancel' : 'pending';

            return (
              <motion.div 
                key={task.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.1 }}
                className={`p-4 border rounded-xl flex gap-4 ${bgClass}`}
              >
                <span className={`material-symbols-outlined ${colorClass} text-[20px] mt-0.5`}>{icon}</span>
                <div>
                  <h4 className="font-headline text-sm text-on-surface mb-1 leading-tight">{task.title}</h4>
                  <p className="font-body text-[11px] text-on-surface-variant line-clamp-2 italic mb-2">
                    {task.result_summary || task.task_payload}
                  </p>
                  <div className="flex items-center gap-2">
                    <span className={`font-label text-[9px] uppercase tracking-widest ${colorClass}`}>
                      {task.status ? task.status.replace('_', ' ') : 'UNKNOWN'}
                    </span>
                    <span className="text-[10px] text-outline/50">•</span>
                    <span className="font-label text-[9px] text-outline">
                      {task.completed_at ? new Date(task.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Active'}
                    </span>
                  </div>
                </div>
              </motion.div>
            );
          })
        ) : (
           <div className="text-center py-10 opacity-50 flex flex-col items-center">
             <span className="material-symbols-outlined text-[32px] mb-2">inbox</span>
             <p className="font-label text-xs uppercase tracking-widest text-outline">No recent outcomes</p>
           </div>
        )}
      </div>
    </div>
  );
}

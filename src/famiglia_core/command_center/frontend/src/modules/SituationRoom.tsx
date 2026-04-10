import type { Task, ActionLog } from '../types';
import { HeroSection } from './ui/HeroSection';
import { OpsPulse } from './ui/OpsPulse';
import { IntelligenceFeed } from './ui/IntelligenceFeed';
import { InsightsTicker } from './ui/InsightsTicker';

interface SituationRoomProps {
  actions: ActionLog[];
  tasks: Task[];
  honorific: string;
  onExecuteDirective: () => void;
}

export function SituationRoom({ actions, tasks, honorific, onExecuteDirective }: SituationRoomProps) {
  const completedTasks = (tasks || []).filter(t => t?.status === 'completed' || t?.status === 'success').length;
  const scheduledTasks = (tasks || []).filter(t => t?.status === 'pending').length;
  const failedTasks = (tasks || []).filter(t => t?.status === 'failed').length;

  return (
    <div data-testid="situation-room">
      <HeroSection honorific={honorific} onExecuteDirective={onExecuteDirective} />
      <div className="grid grid-cols-12 gap-6 items-start">
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-6">
          <OpsPulse
            completedTasks={completedTasks}
            scheduledTasks={scheduledTasks}
            failedTasks={failedTasks}
            tasks={tasks}
          />
          <InsightsTicker />
        </div>
        <IntelligenceFeed actions={actions} />
      </div>
    </div>
  );
}

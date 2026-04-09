import type { Action, Task, GraphDefinition } from '../types';
import { HeroSection } from './ui/HeroSection';
import { OpsPulse } from './ui/OpsPulse';
import { IntelligenceFeed } from './ui/IntelligenceFeed';
import { InsightsTicker } from './ui/InsightsTicker';
import { LatestMissions } from './ui/LatestMissions';
import { OperationsHub } from './ui/OperationsHub';

interface SituationRoomProps {
  actions: Action[];
  tasks: Task[];
  graphs?: GraphDefinition[];
  honorific: string;
}

export function SituationRoom({ actions, tasks, graphs = [], honorific }: SituationRoomProps) {
  const completedTasks = (tasks || []).filter(t => t?.status === 'completed' || t?.status === 'success').length;
  const scheduledTasks = (tasks || []).filter(t => t?.status === 'pending').length;
  const failedTasks = (tasks || []).filter(t => t?.status === 'failed').length;

  return (
    <>
      <HeroSection honorific={honorific} />
      <div className="grid grid-cols-12 gap-6 items-start">
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-6">
          <OpsPulse completedTasks={completedTasks} scheduledTasks={scheduledTasks} failedTasks={failedTasks} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 min-h-[400px]">
            <LatestMissions tasks={tasks} />
            <OperationsHub graphs={graphs} />
          </div>
          <InsightsTicker />
        </div>
        <IntelligenceFeed actions={actions} />
      </div>
    </>
  );
}

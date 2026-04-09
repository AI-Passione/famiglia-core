import type { Agent, Action, Task, GraphDefinition } from '../types';
import { HeroSection } from './ui/HeroSection';
import { OpsPulse } from './ui/OpsPulse';
import { IntelligenceFeed } from './ui/IntelligenceFeed';
import { InsightsTicker } from './ui/InsightsTicker';
import { LatestMissions } from './ui/LatestMissions';
import { OperationsHub } from './ui/OperationsHub';

interface SituationRoomProps {
  agents: Agent[];
  actions: Action[];
  tasks: Task[];
  graphs?: GraphDefinition[];
  honorific: string;
}

export function SituationRoom({ agents, actions, tasks, graphs = [], honorific }: SituationRoomProps) {
  return (
    <>
      <HeroSection honorific={honorific} />
      <div className="grid grid-cols-12 gap-6 items-start">
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-6">
          <InsightsTicker />
          <OpsPulse agentsCount={(agents || []).length} highPriorityCount={(tasks || []).filter(t => t?.priority === 'high').length} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 min-h-[400px]">
            <LatestMissions tasks={tasks} />
            <OperationsHub graphs={graphs} />
          </div>
        </div>
        <IntelligenceFeed actions={actions} />
      </div>
    </>
  );
}

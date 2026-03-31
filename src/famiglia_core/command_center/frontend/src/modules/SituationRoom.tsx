import type { Agent, Action, Task } from '../types';
import { HeroSection } from './ui/HeroSection';
import { OpsPulse } from './ui/OpsPulse';
import { IntelligenceFeed } from './ui/IntelligenceFeed';
import { DirectivesGrid } from './ui/DirectivesGrid';
import { SystemHealth } from './ui/SystemHealth';

interface SituationRoomProps {
  agents: Agent[];
  actions: Action[];
  tasks: Task[];
}

export function SituationRoom({ agents, actions, tasks }: SituationRoomProps) {
  return (
    <>
      <HeroSection />
      <div className="grid grid-cols-12 gap-6">
        <OpsPulse agentsCount={agents.length} highPriorityCount={tasks.filter(t => t.priority === 'high').length} />
        <IntelligenceFeed actions={actions} />
        <DirectivesGrid tasks={tasks} />
        <SystemHealth />
      </div>
    </>
  );
}

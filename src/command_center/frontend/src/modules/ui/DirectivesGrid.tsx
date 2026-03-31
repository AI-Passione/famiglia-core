import type { Task } from '../../types';

interface DirectiveCardProps {
  task: Task;
  index: number;
}

function DirectiveCard({ task, index }: DirectiveCardProps) {
  const colors = ['tertiary', 'primary', 'outline'];
  const icons = ['history_edu', 'shield', 'diversity_3'];
  const color = colors[index % 3];
  const icon = icons[index % 3];
  
  return (
    <div className={`glass-module p-6 border border-white/5 group hover:border-${color}/20 transition-all`}>
      <div className="flex justify-between mb-4">
        <span className={`font-label text-[10px] text-${color} tracking-widest uppercase`}>Directive {task.id}</span>
        <span className={`material-symbols-outlined text-${color}/40 group-hover:text-${color} transition-colors`}>{icon}</span>
      </div>
      <h4 className="font-headline text-lg text-on-surface mb-2">{task.title}</h4>
      <p className="font-body text-sm text-on-surface-variant mb-6 line-clamp-2">{task.task_payload}</p>
      <div className="flex justify-between items-center">
        <span className={`px-2 py-1 bg-${color}/10 text-${color} font-label text-[9px] uppercase tracking-tighter capitalize`}>{task.status.replace(/_/g, ' ')}</span>
        <button className="text-on-surface hover:text-primary transition-colors">
          <span className="material-symbols-outlined">arrow_forward</span>
        </button>
      </div>
    </div>
  );
}

interface PlaceholderDirectiveProps {
  id: string;
  title: string;
  text: string;
  status: string;
  color: string;
  icon: string;
}

function PlaceholderDirective({ id, title, text, status, color, icon }: PlaceholderDirectiveProps) {
  return (
    <div className={`glass-module p-6 border border-white/5 group hover:border-${color}/20 transition-all opacity-50`}>
      <div className="flex justify-between mb-4">
        <span className={`font-label text-[10px] text-${color} tracking-widest uppercase`}>Directive {id}</span>
        <span className={`material-symbols-outlined text-${color}/40 group-hover:text-${color} transition-colors`}>{icon}</span>
      </div>
      <h4 className="font-headline text-lg text-on-surface mb-2">{title}</h4>
      <p className="font-body text-sm text-on-surface-variant mb-6">{text}</p>
      <div className="flex justify-between items-center">
        <span className={`px-2 py-1 bg-${color}/10 text-${color} font-label text-[9px] uppercase tracking-tighter`}>{status}</span>
        <button className="text-on-surface hover:text-primary transition-colors">
          <span className="material-symbols-outlined">arrow_forward</span>
        </button>
      </div>
    </div>
  );
}

interface DirectivesGridProps {
  tasks: Task[];
}

export function DirectivesGrid({ tasks }: DirectivesGridProps) {
  return (
    <div className="col-span-12 grid grid-cols-1 md:grid-cols-3 gap-6">
      {tasks.length > 0 ? tasks.map((task, idx) => (
        <DirectiveCard key={task.id} task={task} index={idx} />
      )) : (
        <>
          <PlaceholderDirective id="09-A" title="The Venetian Protocol" text="Redirect all Mediterranean assets to secure the North trade corridor by 0400." status="In Progress" color="tertiary" icon="history_edu" />
          <PlaceholderDirective id="14-C" title="Silent Encryption" text="Upgrade all comms to 2048-bit lattice-based encryption immediately." status="Priority High" color="primary" icon="shield" />
          <PlaceholderDirective id="02-B" title="Personnel Rotation" text="Shift Section 3 night watch to the Lounge for de-escalation briefing." status="Pending" color="outline" icon="diversity_3" />
        </>
      )}
    </div>
  );
}

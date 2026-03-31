interface HealthModuleProps {
  icon: string;
  label: string;
  value: number;
  subtext: string;
  color: string;
  accent: string;
}

function HealthModule({ icon, label, value, subtext, color, accent }: HealthModuleProps) {
  return (
    <div className="col-span-12 lg:col-span-4 bg-surface-container-lowest p-6 border-b-2" style={{ borderBottomColor: color === 'primary-container' ? '#4c000f' : color === 'outline-variant' ? '#554240' : color }}>
      <div className="flex items-center gap-4 mb-4">
        <span className={`material-symbols-outlined text-${accent}`}>{icon}</span>
        <h5 className="font-label text-xs tracking-widest text-outline uppercase">{label}</h5>
      </div>
      <div className="w-full bg-surface-container-high h-1 mb-2">
        <div className={`h-full bg-${accent}`} style={{ width: `${value}%` }}></div>
      </div>
      <p className="font-label text-[10px] text-on-surface-variant">{subtext}</p>
    </div>
  );
}

export function SystemHealth() {
  return (
    <>
      <HealthModule icon="biotech" label="AI Neural Integrity" value={94.2} subtext="Cognitive Consistency: 94.2%" color="#4A0404" accent="tertiary" />
      <HealthModule icon="database" label="Archive Sync Rate" value={88} subtext="Intelligences Indexed: 14.2TB/sec" color="primary-container" accent="primary" />
      <HealthModule icon="hub" label="Node Connectivity" value={99} subtext="1,204 Active Nodes Connected" color="outline-variant" accent="on-surface" />
    </>
  );
}

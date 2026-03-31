interface PulseStatProps {
  value: string;
  label: string;
  color: string;
}

function PulseStat({ value, label, color }: PulseStatProps) {
  const colorClass = color === 'tertiary' ? 'text-tertiary' : color === 'primary' ? 'text-primary' : 'text-on-surface';
  return (
    <div>
      <p className={`font-label ${colorClass} text-3xl font-bold`}>{value}</p>
      <p className="font-label text-outline text-[10px] uppercase tracking-tighter">{label}</p>
    </div>
  );
}

interface OpsUpdateProps {
  location: string;
  text: string;
  borderColor: string;
}

function OpsUpdate({ location, text, borderColor }: OpsUpdateProps) {
  return (
    <div className={`flex-1 bg-surface-container-highest/20 p-4 border-l-2`} style={{ borderColor }}>
      <p className="font-label text-[10px] text-outline uppercase tracking-widest mb-1">Last Update: {location}</p>
      <p className="font-body text-sm text-on-surface-variant italic">"{text}"</p>
    </div>
  );
}

interface OpsPulseProps {
  agentsCount: number;
  highPriorityCount: number;
}

export function OpsPulse({ agentsCount, highPriorityCount }: OpsPulseProps) {
  return (
    <div className="col-span-12 lg:col-span-8 bg-surface-container-low p-8 relative overflow-hidden min-h-[400px]">
      <div className="absolute top-0 right-0 p-8">
        <span className="font-label text-[10px] text-outline tracking-widest uppercase">Live Telemetry</span>
      </div>
      <h3 className="font-headline text-2xl text-on-surface mb-8">Global Operations Pulse</h3>
      <div className="relative w-full h-64 mt-4 bg-surface-container-lowest/50 rounded-sm border border-outline-variant/5">
        <img 
          alt="Global Operations" 
          className="w-full h-full object-cover opacity-20 mix-blend-luminosity" 
          src="https://lh3.googleusercontent.com/aida-public/AB6AXuBS_nd5k3Lz3Eeof7r4EHQ_aECP5fgF5I3uv8oLsOpnADsLRGfNT95K8R5tkOCmYaRfdgcMAXg_V-DkAP2Jem7zcwKglCN_xFpBKl2Qo-gpqgWn9LLMIkJUYuIjsOplEhKlLxhWA9LF13ryPvs_PuBeZoVXJR_PrXpu2hoC2sG5JUp8qzZHpxxZ7iNpKrS6I5tQ-euRJPYC0yOZa3owsX8PJVUVCGhJTFQ2POi0Rqax0bgaRYqNfmUgoMHmgZ3IY18rfvh-z-DsEhI" 
        />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="grid grid-cols-3 gap-12 text-center">
            <PulseStat value={agentsCount.toString().padStart(2, '0')} label="Active Agents" color="tertiary" />
            <PulseStat value={highPriorityCount.toString().padStart(2, '0')} label="High Priority" color="primary" />
            <PulseStat value="28ms" label="System Latency" color="on-surface" />
          </div>
        </div>
      </div>
      <div className="mt-8 flex gap-4">
        <OpsUpdate location="Rome" text="Package secured. Proceeding to safehouse 7." borderColor="primary-container" />
        <OpsUpdate location="Tokyo" text="Surveillance established. Awaiting signal." borderColor="tertiary/40" />
      </div>
    </div>
  );
}

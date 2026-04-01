interface HeroSectionProps {
  honorific: string;
}

export function HeroSection({ honorific }: HeroSectionProps) {
  return (
    <section className="flex justify-between items-end border-b border-outline-variant/10 pb-8">
      <div>
        <h2 className="font-headline text-4xl font-bold text-on-surface tracking-tight">The Situation Room</h2>
        <p className="font-headline text-lg text-[#ffb3b5] mt-2">Welcome back, {honorific}</p>
        <p className="font-label text-tertiary text-xs tracking-widest uppercase mt-2">Active Protocol: Nightfall | Operational Level: Alpha</p>
      </div>
      <div className="flex items-center gap-4">
        <button className="bg-[#4A0404] text-white px-6 py-2.5 font-label text-xs uppercase tracking-widest hover:brightness-110 transition-all rounded-sm flex items-center gap-2">
          <span className="material-symbols-outlined text-sm">bolt</span>
          Execute Directive
        </button>
        <div className="bg-surface-container-low px-4 py-2 flex items-center gap-3">
          <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span>
          <span className="font-label text-xs text-secondary-fixed-dim">SYSTEM UPTIME: 99.98%</span>
        </div>
      </div>
    </section>
  );
}

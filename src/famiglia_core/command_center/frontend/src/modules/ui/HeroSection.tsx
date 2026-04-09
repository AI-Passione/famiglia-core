interface HeroSectionProps {
  honorific: string;
  onExecuteDirective: () => void;
}

export function HeroSection({ honorific, onExecuteDirective }: HeroSectionProps) {
  return (
    <section className="flex justify-between items-end border-b border-outline-variant/10 pb-8">
      <div>
        <h2 className="font-headline text-4xl font-bold text-on-surface tracking-tight">The Situation Room</h2>
        <p className="font-headline text-lg text-[#ffb3b5] mt-2">Welcome back, {honorific}</p>

      </div>
      <div className="flex items-center gap-4">
        <button 
          onClick={onExecuteDirective}
          className="bg-[#4A0404] text-white px-6 py-2.5 font-label text-xs uppercase tracking-widest hover:brightness-110 active:scale-95 transition-all rounded-sm flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">bolt</span>
          Execute Directive
        </button>
        <div className="bg-surface-container-low px-4 py-2 flex items-center gap-3">
          <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span>
          <span className="font-label text-xs text-secondary-fixed-dim">ENGINE ROOM: ONLINE</span>
        </div>
      </div>
    </section>
  );
}

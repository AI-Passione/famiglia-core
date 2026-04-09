interface NavIconButtonProps {
  icon: string;
}

function NavIconButton({ icon }: NavIconButtonProps) {
  return (
    <button className="text-[#ffb3b5] hover:scale-110 active:opacity-80 transition-all duration-300">
      <span className="material-symbols-outlined">{icon}</span>
    </button>
  );
}

export function TopNav() {
  return (
    <header className="fixed top-0 w-full z-50 flex justify-between items-center px-8 h-16 bg-[#131313]/80 backdrop-blur-xl border-b border-white/5 shadow-2xl">
      <div className="flex items-center gap-4 group">
        <div className="relative">
          <div className="absolute -inset-1 bg-gradient-to-r from-[#ffb3b5] to-[#f59e0b] rounded-full blur opacity-20 group-hover:opacity-40 transition duration-1000 group-hover:duration-200"></div>
          <img 
            src="/logo.png" 
            alt="Famiglia Core Logo" 
            className="relative h-9 w-9 rounded-full border border-white/10"
          />
        </div>
        <div className="flex items-center gap-3">
          <span className="font-headline italic text-2xl text-[#ffb3b5] drop-shadow-[0_0_8px_rgba(255,179,181,0.3)]">
            Famiglia Core
          </span>
          <a
            href="https://github.com/AI-Passione/famiglia-core"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 hover:border-[#ffb3b5]/30 transition-all duration-300 group/github"
            title="View Source on GitHub"
          >
            <svg className="w-4.5 h-4.5 group-hover/github:scale-110 transition-all duration-300">
              <use href="/icons.svg#github-icon" />
            </svg>
          </a>
        </div>
      </div>
      <div className="hidden md:flex items-center space-x-8">
        <div className="flex items-center gap-4 ml-8">
          <NavIconButton icon="search" />
          <NavIconButton icon="notifications" />
          <NavIconButton icon="account_circle" />
        </div>
      </div>
    </header>
  );
}

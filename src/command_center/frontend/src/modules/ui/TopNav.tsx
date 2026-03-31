interface NavIconButtonProps {
  icon: string;
}

function NavIconButton({ icon }: NavIconButtonProps) {
  return (
    <button className="text-[#ffb3b5] hover:scale-95 active:opacity-80 transition-all">
      <span className="material-symbols-outlined">{icon}</span>
    </button>
  );
}

export function TopNav() {
  return (
    <header className="fixed top-0 w-full z-50 flex justify-between items-center px-8 h-16 bg-[#131313]">
      <div className="flex items-center gap-4">
        <span className="font-headline italic text-2xl text-[#ffb3b5]">La Passione Inc.</span>
      </div>
      <div className="hidden md:flex items-center space-x-8">
        <div className="flex items-center gap-4 ml-8">
          <NavIconButton icon="search" />
          <NavIconButton icon="notifications" />
          <NavIconButton icon="account_circle" />
        </div>
      </div>
      <div className="fixed top-16 w-full z-50 bg-[#1c1b1b] h-[1px]"></div>
    </header>
  );
}

export function Sidebar({ activeTab, setActiveTab }: any) {
  const mainItems = [
    { id: 'situation_room', label: 'The Situation Room', icon: 'dashboard' },
    { id: 'operations', label: 'Operations', icon: 'description' },
    { id: 'agenda', label: 'The Agenda', icon: 'calendar_month' },
    { id: 'famiglia', label: 'The Famiglia', icon: 'groups' },
  ];

  const secondaryItems = [
    { id: 'intelligences', label: 'Intelligences', icon: 'insights' },
    { id: 'terminal', label: 'The Terminal', icon: 'chat' },
  ];

  return (
    <aside className="fixed left-0 top-0 h-full z-40 flex flex-col py-6 bg-[#131313] w-72 border-r border-[#1c1b1b]">
      <div className="px-8 mt-16 mb-10">
        <h1 className="font-headline text-xl text-[#ffb3b5] tracking-tighter">La Passione Inc.</h1>
        <p className="font-body font-medium text-[10px] tracking-widest text-[#a38b88] uppercase mt-1">The Silent Concierge</p>
      </div>

      <nav className="px-4 space-y-1">
        {mainItems.map(item => (
          <button
            type="button"
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`w-full flex items-center gap-4 px-4 py-3 rounded-sm transition-all duration-200 ${activeTab === item.id
              ? 'translate-x-1 text-[#ffb3b5] font-bold bg-[#1c1b1b] border-l-4 border-[#4A0404]'
              : 'hover:text-[#ffb3b5] text-[#a38b88] hover:bg-[#1c1b1b]/50'
              }`}
          >
            <span className="material-symbols-outlined">{item.icon}</span>
            <span className="font-body font-medium text-sm tracking-wide">{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="px-4 mt-auto space-y-1">
        <div className="pt-6 border-t border-[#1c1b1b]/50 mb-2 invisible" />
        {secondaryItems.map(item => (
          <button
            type="button"
            key={item.id}
            onClick={() => {
              if (item.id === 'terminal') {
                window.open('/terminal.html', '_blank');
              } else if (item.id === 'intelligences') {
                window.open('/intelligence.html', '_blank');
              } else {
                setActiveTab(item.id);
              }
            }}
            className={`w-full flex items-center gap-4 px-4 py-3 rounded-sm transition-all duration-200 ${activeTab === item.id
              ? 'translate-x-1 text-[#ffb3b5] font-bold bg-[#1c1b1b] border-l-4 border-[#4A0404]'
              : 'hover:text-[#ffb3b5] text-[#a38b88] hover:bg-[#1c1b1b]/50'
              }`}
          >
            <span className="material-symbols-outlined">{item.icon}</span>
            <span className="font-body font-medium text-sm tracking-wide">{item.label}</span>
          </button>
        ))}
        <button
          type="button"
          onClick={() => setActiveTab('settings')}
          className={`w-full flex items-center gap-4 px-4 py-3 rounded-sm transition-all duration-200 ${activeTab === 'settings'
            ? 'translate-x-1 text-[#ffb3b5] font-bold bg-[#1c1b1b] border-l-4 border-[#4A0404]'
            : 'hover:text-[#ffb3b5] text-[#a38b88] hover:bg-[#1c1b1b]/50'
            }`}
        >
          <span className="material-symbols-outlined">settings</span>
          <span className="font-body font-medium text-sm tracking-wide">Settings</span>
        </button>
      </div>
    </aside>
  );
}

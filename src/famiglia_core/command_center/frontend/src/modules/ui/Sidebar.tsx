export function Sidebar({ activeTab, setActiveTab }: any) {
  const items = [
    { id: 'situation_room', label: 'The Situation Room', icon: 'dashboard' },
    { id: 'sop', label: 'SOP', icon: 'description' },
    { id: 'famiglia', label: 'The Famiglia', icon: 'groups' },
    { id: 'intelligences', label: 'Intelligences', icon: 'insights' },
    { id: 'connections', label: 'Connections', icon: 'hub' },
  ];

  return (
    <aside className="fixed left-0 top-0 h-full z-40 flex flex-col py-6 bg-[#131313] w-72 border-r border-[#1c1b1b]">
      <div className="px-8 mt-16 mb-10">
        <h1 className="font-headline text-xl text-[#ffb3b5] tracking-tighter">La Passione Inc.</h1>
        <p className="font-body font-medium text-[10px] tracking-widest text-[#a38b88] uppercase mt-1">The Silent Concierge</p>
      </div>
      <nav className="flex-1 px-4 space-y-1">
        {items.map(item => (
          <button
            type="button"
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`w-full flex items-center gap-4 px-4 py-3 rounded-sm transition-all duration-200 ${
              activeTab === item.id 
              ? 'translate-x-1 text-[#ffb3b5] font-bold bg-[#1c1b1b] border-l-4 border-[#4A0404]' 
              : 'hover:text-[#ffb3b5] text-[#a38b88] hover:bg-[#1c1b1b]/50'
            }`}
          >
            <span className="material-symbols-outlined">{item.icon}</span>
            <span className="font-body font-medium text-sm tracking-wide">{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="px-4 mt-auto pt-6 space-y-1">
        <button
          type="button"
          onClick={() => setActiveTab('settings')}
          className={`w-full flex items-center gap-4 px-4 py-3 rounded-sm transition-all duration-200 ${
            activeTab === 'settings'
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

export function DirectivesTerminal() {
  return (
    <div className="fixed bottom-8 right-8 z-[60]">
      <button className="bg-[#4A0404] text-white rounded-full p-4 shadow-[0px_24px_48px_rgba(0,0,0,0.4)] hover:scale-110 hover:shadow-lg transition-transform active:scale-90 duration-150 flex items-center gap-3">
        <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>chat</span>
        <span className="font-label text-[10px] uppercase tracking-widest font-bold pr-2">Directives Terminal</span>
      </button>
    </div>
  );
}

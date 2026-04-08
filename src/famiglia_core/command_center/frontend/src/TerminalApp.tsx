import { Terminal } from './modules/Terminal';
import { TerminalProvider } from './modules/TerminalContext';

export function TerminalApp() {
  return (
    <TerminalProvider>
      <div className="h-screen bg-background p-6 font-body flex flex-col overflow-hidden">
        <header className="mb-6 flex items-center justify-between px-2">
           <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-3xl text-primary">terminal</span>
              <h1 className="font-headline italic text-2xl text-primary tracking-tight">The Directive Terminal</h1>
           </div>
           <div className="flex items-center gap-4 text-outline text-[10px] uppercase tracking-widest font-label">
              <span className="flex items-center gap-2">
                 <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                 Live Connection
              </span>
              <span className="opacity-50">v2.1.0-Passione</span>
           </div>
        </header>
        
        <div className="flex-1 min-h-0 bg-surface-container-lowest/20 rounded-[32px] border border-outline/5 overflow-hidden shadow-2xl">
           <Terminal />
        </div>

        <footer className="mt-4 px-4 flex justify-between items-center opacity-30 pointer-events-none">
           <span className="text-[9px] uppercase tracking-[0.2em]">Secure Terminal • Multi-Agent Orchestration • La Passione Inc.</span>
           <span className="text-[9px] font-label">Don Jimmy Access Authorized</span>
        </footer>
      </div>
    </TerminalProvider>
  );
}

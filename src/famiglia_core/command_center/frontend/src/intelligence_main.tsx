import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Intelligences } from './modules/Intelligences.tsx'
import { TerminalProvider } from './modules/TerminalContext'
import { NotificationProvider } from './modules/NotificationContext'
import { DirectivesTerminal } from './modules/ui/DirectivesTerminal'
import './index.css'

function IntelligenceApp() {
  return (
    <NotificationProvider>
      <TerminalProvider initialChatId="intelligence-hub">
      <div className="bg-background text-on-background font-body min-h-screen selection:bg-primary/30 relative">
        {/* Background Map Overlay to maintain "La Passione" vibe */}
        <div className="fixed inset-0 noir-bg-map pointer-events-none opacity-20 z-0"></div>
        
        {/* Main Content */}
        <main className="relative z-10 p-8 h-screen overflow-hidden flex flex-col">
          <div className="flex items-center gap-4 mb-8">
            <div className="w-10 h-10 bg-primary/20 rounded-lg flex items-center justify-center border border-primary/30">
              <span className="material-symbols-outlined text-primary">folder_managed</span>
            </div>
            <div>
              <h1 className="text-xl font-black font-title text-white tracking-widest uppercase">Intelligence Center</h1>
              <p className="text-[10px] text-outline font-black uppercase tracking-tighter">Rossini Data Layer v4.0</p>
            </div>
          </div>
          
          <div className="flex-1 overflow-hidden rounded-xl border border-outline-variant/10 shadow-2xl bg-surface-container-lowest/20 backdrop-blur-md">
            <Intelligences />
          </div>
        </main>

        <DirectivesTerminal />
      </div>
      </TerminalProvider>
    </NotificationProvider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <IntelligenceApp />
  </StrictMode>,
)

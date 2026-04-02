import { useState, useEffect } from 'react';
import { Terminal } from './modules/Terminal';
import { API_BASE } from './config';
import type { Agent, ActionLog } from './types';

export function TerminalApp() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [actions, setActions] = useState<ActionLog[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [agentsRes, actionsRes] = await Promise.all([
          fetch(`${API_BASE}/agents`),
          fetch(`${API_BASE}/actions?limit=24`)
        ]);
        if (agentsRes.ok) {
           const agentsData = await agentsRes.json();
           setAgents(agentsData);
        }
        if (actionsRes.ok) {
           const data = await actionsRes.json();
           setActions(data.actions || []);
        }
      } catch (error) {
        console.error('Failed to fetch data for Terminal standalone.', error);
      }
    };
    fetchData();
    // Refresh data every 30 seconds for the standalone terminal
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-background p-6 font-body flex flex-col overflow-hidden">
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
         <Terminal agents={agents} actions={actions} />
      </div>

      <footer className="mt-4 px-4 flex justify-between items-center opacity-30 pointer-events-none">
         <span className="text-[9px] uppercase tracking-[0.2em]">Secure Terminal • Multi-Agent Orchestration • La Passione Inc.</span>
         <span className="text-[9px] font-label">Don Jimmy Access Authorized</span>
      </footer>
    </div>
  );
}

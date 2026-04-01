import { useEffect, useMemo, useState } from 'react';
import type { FamigliaAgent } from '../types';
import { API_BASE } from '../config';

function normalizeStatus(status: string): 'active' | 'inactive' {
  const value = (status || '').toLowerCase();
  return ['active', 'online', 'idle', 'thinking'].includes(value) ? 'active' : 'inactive';
}

function initialsFor(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0]?.toUpperCase() || '')
    .join('');
}

export function Famiglia() {
  const [agents, setAgents] = useState<FamigliaAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadRoster = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`${API_BASE}/famiglia/agents`);
        if (!response.ok) throw new Error('Failed to load agent roster');
        const payload = await response.json();
        setAgents(Array.isArray(payload) ? (payload as FamigliaAgent[]) : []);
      } catch (err) {
        console.error(err);
        setError('Unable to load The Famiglia roster from Notion.');
      } finally {
        setLoading(false);
      }
    };

    loadRoster();
  }, []);

  const activeCount = useMemo(
    () => agents.filter(agent => normalizeStatus(agent.status) === 'active').length,
    [agents]
  );

  if (loading) {
    return (
      <div className="py-20 flex items-center justify-center text-[#ffb3b5] opacity-40">
        <span className="material-symbols-outlined animate-spin text-4xl">nest_remote_comfort_sensor</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-[#161616] border border-[#4A0404] p-8">
        <h2 className="font-headline text-2xl text-white">The Famiglia</h2>
        <p className="font-body text-[#ffb3b5] mt-4">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-headline text-5xl font-bold text-white tracking-tight">Agent Roster</h1>
          <p className="font-body text-outline mt-3 max-w-3xl">
            Full active/inactive AI personnel index sourced from the Agent Roster Notion database.
          </p>
        </div>
        <div className="font-label uppercase text-[11px] tracking-widest text-tertiary">
          {activeCount} Active Agents
        </div>
      </header>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {agents.map(agent => {
          const status = normalizeStatus(agent.status);
          return (
            <article
              key={agent.id}
              className="bg-surface-container-low border border-outline-variant/20 p-6 space-y-5"
            >
              <div className="flex items-start gap-4">
                <div className="w-16 h-16 bg-surface-container-lowest overflow-hidden flex items-center justify-center text-outline font-headline">
                  {agent.profile_pic_url ? (
                    <img
                      src={agent.profile_pic_url}
                      alt={`${agent.name} profile`}
                      className="w-full h-full object-cover grayscale"
                    />
                  ) : (
                    initialsFor(agent.name)
                  )}
                </div>
                <div className="flex-1">
                  <h2 className="font-headline text-2xl text-white">{agent.name}</h2>
                  <p className="font-label text-[11px] uppercase tracking-widest text-outline mt-1">{agent.role}</p>
                </div>
                <span
                  className={`px-2 py-1 font-label text-[10px] uppercase tracking-widest border ${
                    status === 'active'
                      ? 'text-tertiary border-tertiary/40 bg-on-tertiary-fixed-variant/20'
                      : 'text-outline border-outline/30'
                  }`}
                >
                  {status}
                </span>
              </div>

              <div className="space-y-4 text-sm">
                <div>
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-outline mb-1">Soul Definition</p>
                  <p className="font-body text-on-surface-variant italic">"{agent.personality}"</p>
                </div>
                <div>
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-outline mb-1">Skills</p>
                  <p className="font-body text-on-surface-variant">{agent.skills.join(', ') || 'No skills listed.'}</p>
                </div>
                <div>
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-outline mb-1">Tools</p>
                  <p className="font-body text-on-surface-variant">{agent.tools.join(', ') || 'No tools listed.'}</p>
                </div>
                <div>
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-outline mb-1">Assigned Projects</p>
                  <p className="font-body text-on-surface-variant">
                    {agent.assigned_projects.join(', ') || 'No active projects assigned.'}
                  </p>
                </div>
                <div>
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-outline mb-1">Latest Conversation</p>
                  <p className="font-body text-on-surface-variant">"{agent.latest_conversation_snippet}"</p>
                </div>
              </div>
            </article>
          );
        })}
      </section>
    </div>
  );
}

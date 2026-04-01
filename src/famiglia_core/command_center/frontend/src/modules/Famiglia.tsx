import { useEffect, useMemo, useState } from 'react';
import type { FamigliaAgent } from '../types';
import { API_BASE, BACKEND_BASE } from '../config';
import { AgentEditModal } from './AgentEditModal';

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

function formatLastActive(value: string | null): string {
  if (!value) return 'No recent activity';

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'No recent activity';

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(parsed);
}

function renderList(values: string[], fallback: string): string {
  return values.length > 0 ? values.join(', ') : fallback;
}

export function Famiglia() {
  const [agents, setAgents] = useState<FamigliaAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingAgent, setEditingAgent] = useState<FamigliaAgent | null>(null);

  const loadRoster = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/famiglia/agents`);
      if (!response.ok) throw new Error('Failed to load agent roster');
      const payload = await response.json();
      setAgents(Array.isArray(payload) ? (payload as FamigliaAgent[]) : []);
    } catch (err) {
      console.error(err);
      setError('Unable to load The Famiglia roster from PostgreSQL.');
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    loadRoster();
  }, []);

  const activeCount = useMemo(
    () => agents.filter(agent => normalizeStatus(agent.status) === 'active').length,
    [agents]
  );
  const totalCount = agents.length;

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
            PostgreSQL-backed roster sourced from the `agents` table, enriched with linked skills, tools, workflows, and recent message history.
          </p>
        </div>
        <div className="text-right">
          <div className="font-label uppercase text-[11px] tracking-widest text-tertiary">
            {activeCount} Active Agents
          </div>
          <div className="font-label uppercase text-[11px] tracking-widest text-outline mt-2">
            {totalCount} Total Souls
          </div>
        </div>
      </header>

      {agents.length === 0 && (
        <section className="border border-outline-variant/20 bg-surface-container-low p-8">
          <h2 className="font-headline text-2xl text-white">No agents found</h2>
          <p className="font-body text-on-surface-variant mt-3 max-w-2xl">
            The roster is now driven directly from PostgreSQL. Seed or sync the `agents` table to make this page come alive.
          </p>
        </section>
      )}

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {agents.map(agent => {
          const status = normalizeStatus(agent.status);
          return (
            <article
              key={agent.id}
              className="bg-surface-container-low border border-outline-variant/20 p-6 space-y-5"
            >
              <div className="flex items-start gap-4">
                <div className="w-16 h-16 bg-surface-container-lowest overflow-hidden flex items-center justify-center text-outline font-headline relative group">
                  {agent.avatar_url ? (
                    <>
                      <img
                        src={`${BACKEND_BASE}${agent.avatar_url}`}
                        alt={agent.name}
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = 'none';
                        }}
                      />
                      <div className="absolute inset-0 border border-white/10 group-hover:border-tertiary/30 transition-colors pointer-events-none" />
                    </>
                  ) : (
                    <span>{initialsFor(agent.name)}</span>
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-start">
                    <div>
                      <h2 className="font-headline text-2xl text-white">{agent.name}</h2>
                      <p className="font-label text-[11px] uppercase tracking-widest text-outline mt-1">
                        {agent.role}
                      </p>
                    </div>
                    <button
                      onClick={() => setEditingAgent(agent)}
                      className="p-2 text-on-surface-variant hover:text-tertiary transition-colors group/edit"
                      title="Edit Agent Dossier"
                    >
                      <svg className="w-5 h-5 transition-transform group-hover/edit:scale-110" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </button>
                  </div>
                </div>
                <span
                  className={`px-2 py-1 font-label text-[10px] uppercase tracking-widest border ${status === 'active'
                      ? 'text-tertiary border-tertiary/40 bg-on-tertiary-fixed-variant/20'
                      : 'text-outline border-outline/30'
                    }`}
                >
                  {status}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-outline mb-1">Aliases</p>
                  <p className="font-body text-on-surface-variant">
                    {renderList(agent.aliases, 'No aliases configured.')}
                  </p>
                </div>
                <div>
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-outline mb-1">Last Active</p>
                  <p className="font-body text-on-surface-variant">{formatLastActive(agent.last_active)}</p>
                </div>
              </div>

              <div className="space-y-4 text-sm">
                <div>
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-outline mb-1">Persona</p>
                  <p className="font-body text-on-surface-variant italic">"{agent.personality}"</p>
                </div>
                <div>
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-outline mb-1">Identity</p>
                  <p className="font-body text-on-surface-variant">{agent.identity}</p>
                </div>
                <div>
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-outline mb-1">Skills</p>
                  <p className="font-body text-on-surface-variant">
                    {renderList(agent.skills, 'No skills listed.')}
                  </p>
                </div>
                <div>
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-outline mb-1">Tools</p>
                  <p className="font-body text-on-surface-variant">
                    {renderList(agent.tools, 'No tools listed.')}
                  </p>
                </div>
                <div>
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-outline mb-1">Workflows</p>
                  <p className="font-body text-on-surface-variant">
                    {renderList(agent.workflows, 'No workflows linked yet.')}
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

      {editingAgent && (
        <AgentEditModal
          agent={editingAgent}
          onClose={() => setEditingAgent(null)}
          onSave={() => loadRoster(false)}
        />
      )}
    </div>
  );
}

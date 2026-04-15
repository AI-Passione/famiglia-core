import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  const navigate = useNavigate();

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
    () => agents.filter(agent => agent && normalizeStatus(agent.status) === 'active').length,
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
        <div className="text-right flex items-end gap-6">
          <div className="space-y-1">
            <div className="font-label uppercase text-[11px] tracking-widest text-tertiary">
              {activeCount} Active Agents
            </div>
            <div className="font-label uppercase text-[11px] tracking-widest text-outline">
              {totalCount} Total Souls
            </div>
          </div>
          
          <div className="h-10 w-px bg-white/5 mx-2" />

          <div className="space-y-1">
            <div className="font-label uppercase text-[11px] tracking-widest text-[#ffb3b5]">
              {agents.filter(a => a.is_slack_connected).length}/{totalCount} Connected
            </div>
            <button 
              onClick={() => navigate('/settings?tab=integration')}
              className="font-label uppercase text-[9px] tracking-[0.2em] text-outline hover:text-white transition-colors flex items-center gap-1 group"
            >
              Assemble Famiglia
              <span className="material-symbols-outlined text-[14px] group-hover:translate-x-0.5 transition-transform">arrow_forward</span>
            </button>
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
                  {status}
                </span>

                <div className="flex flex-col items-end gap-2">
                  <div 
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all duration-500 ${
                      agent.is_slack_connected 
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
                        : 'bg-white/5 border-white/10 text-outline grayscale opacity-60'
                    }`}
                    title={agent.is_slack_connected ? 'Live on Slack' : 'Slack Connection Pending'}
                  >
                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.527 2.527 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.527 2.527 0 0 1 2.521 2.521 2.527 2.527 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.958 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.527 2.527 0 0 1-2.52 2.521h-2.522v-2.521zM17.688 8.834a2.527 2.527 0 0 1-2.521 2.521 2.527 2.527 0 0 1-2.521-2.521V2.522A2.528 2.528 0 0 1 15.167 0a2.528 2.528 0 0 1 2.521 2.522v6.312zM15.167 18.958a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.52 2.527 2.527 0 0 1-2.521-2.522v-2.52h2.521zM15.167 17.688a2.527 2.527 0 0 1-2.521-2.521 2.527 2.527 0 0 1 2.521-2.521h6.312a2.528 2.528 0 0 1 2.521 2.52 2.528 2.528 0 0 1-2.521 2.522h-6.312z" />
                    </svg>
                    <span className="font-label text-[9px] uppercase tracking-widest">
                      {agent.is_slack_connected ? 'Connected' : 'Offline'}
                    </span>
                  </div>
                  {!agent.is_slack_connected && (
                    <button 
                      onClick={() => navigate('/settings?tab=integration')}
                      className="text-[9px] uppercase tracking-widest text-[#ffb3b5]/60 hover:text-[#ffb3b5] transition-colors border-b border-[#ffb3b5]/20 hover:border-[#ffb3b5] pb-0.5 ml-auto"
                    >
                      Provision
                    </button>
                  )}
                </div>
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

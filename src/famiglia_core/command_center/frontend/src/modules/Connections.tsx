import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_BASE } from '../config';

interface GitHubStatus {
  connected: boolean;
  username?: string;
  avatar_url?: string;
  scopes?: string;
  connected_at?: string;
}

interface NotionStatus {
  connected: boolean;
  username?: string;
  avatar_url?: string;
  scopes?: string;
  connected_at?: string;
}

interface ServiceConfig {
  configured: boolean;
  redirect_uri: string;
  client_id?: string;
}

type SlackConfig = ServiceConfig;

interface SlackStatus {
  connected: boolean;
  username?: string;
  avatar_url?: string;
  scopes?: string;
  connected_at?: string;
}

interface OllamaStatus {
  connected: boolean;
  connected_at?: string;
}

// Shared API configuration is now imported from ../config.ts

function formatDate(iso?: string) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// ─── Center Popup Helper ───────────────────────────────────────────────────

function openCenterPopup(url: string, title: string, w: number, h: number) {
  if (!window.top) return null;
  const y = window.top.outerHeight / 2 + window.top.screenY - h / 2;
  const x = window.top.outerWidth / 2 + window.top.screenX - w / 2;
  return window.open(
    url,
    title,
    `toolbar=no, location=no, directories=no, status=no, menubar=no, scrollbars=yes, resizable=yes, copyhistory=no, width=${w}, height=${h}, top=${y}, left=${x}`
  );
}

// ─── Setup Guides ─────────────────────────────────────────────────────────

function GitHubSetupGuide() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-8 bg-[#0d0d0d] border border-[#ffb3b5]/10 rounded-xl space-y-6"
    >
      <div className="flex items-center gap-6">
        <div className="p-4 bg-[#4A0404]/30 rounded-xl border border-[#4A0404]/50 shadow-[0_0_20px_rgba(74,4,4,0.2)]">
          <span className="material-symbols-outlined text-[#ffb3b5] text-4xl">settings_input_component</span>
        </div>
        <div>
          <h3 className="text-2xl font-headline font-bold text-white tracking-tighter">Connection Config Pending</h3>
          <p className="text-sm font-body text-[#6b6b6b] mt-1 leading-relaxed">
            Don Jimmy, your GitHub credentials haven't been detected in the vault yet. 
            Once you've added your <strong>Client ID</strong> and <strong>Secret</strong> to the <code>.env</code>, 
            restart the backend to activate the secure sync.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-[#161616] border border-[#232323] rounded-lg space-y-2">
            <span className="text-[10px] font-label font-bold text-[#a38b88] uppercase tracking-widest">Step 1</span>
            <p className="text-[11px] font-body text-[#555] leading-relaxed">
                Add <code>GITHUB_OAUTH_CLIENT_ID</code> and <code>GITHUB_OAUTH_CLIENT_SECRET</code> to your <code>.env</code> file.
            </p>
        </div>
        <div className="p-4 bg-[#161616] border border-[#232323] rounded-lg space-y-2 text-center flex flex-col justify-center">
            <span className="material-symbols-outlined text-[#3a3a3a] text-3xl">restart_alt</span>
            <p className="text-[10px] font-label font-bold text-[#3a3a3a] uppercase tracking-widest mt-2">Restart Backend</p>
        </div>
        <div className="p-4 bg-[#161616] border border-[#232323] rounded-lg space-y-2 text-right">
            <span className="text-[10px] font-label font-bold text-[#a38b88] uppercase tracking-widest">Done?</span>
            <button
                onClick={() => window.location.reload()}
                className="block w-full py-2 bg-[#ffb3b5]/10 text-[#ffb3b5] border border-[#ffb3b5]/20 rounded text-[10px] font-bold font-label uppercase tracking-widest hover:bg-[#ffb3b5]/20 transition-all"
            >
                Refresh UI
            </button>
        </div>
      </div>
    </motion.div>
  );
}


// ─── Integration Cards ──────────────────────────────────────────────────
function NotionSetupGuide() {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-8 bg-[#0d0d0d] border border-[#ffb3b5]/10 rounded-xl space-y-6"
      >
        <div className="flex items-center gap-6">
          <div className="p-4 bg-[#4A0404]/30 rounded-xl border border-[#4A0404]/50 shadow-[0_0_20px_rgba(74,4,4,0.2)]">
            <span className="material-symbols-outlined text-[#ffb3b5] text-4xl">description</span>
          </div>
          <div>
            <h3 className="text-2xl font-headline font-bold text-white tracking-tighter">Notion Handshake Missing</h3>
            <p className="text-sm font-body text-[#6b6b6b] mt-1 leading-relaxed">
              Don Jimmy, the Notion integration must be activated in your <code>.env</code> vault first. 
              Configure your <strong>Public Integration</strong> in the Notion Developer Portal to proceed.
            </p>
          </div>
        </div>
  
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-[#161616] border border-[#232323] rounded-lg space-y-2">
              <span className="text-[10px] font-label font-bold text-[#a38b88] uppercase tracking-widest">Step 1</span>
              <p className="text-[11px] font-body text-[#555] leading-relaxed">
                  Add <code>NOTION_OAUTH_CLIENT_ID</code> and <code>NOTION_OAUTH_CLIENT_SECRET</code> to your <code>.env</code> file.
              </p>
          </div>
          <div className="p-4 bg-[#161616] border border-[#232323] rounded-lg space-y-2 text-center flex flex-col justify-center">
              <span className="material-symbols-outlined text-[#3a3a3a] text-3xl">terminal</span>
              <p className="text-[10px] font-label font-bold text-[#3a3a3a] uppercase tracking-widest mt-2">Update .env</p>
          </div>
          <div className="p-4 bg-[#161616] border border-[#232323] rounded-lg space-y-2 text-right">
              <span className="text-[10px] font-label font-bold text-[#a38b88] uppercase tracking-widest">Ready?</span>
              <button
                  onClick={() => window.location.reload()}
                  className="block w-full py-2 bg-[#ffb3b5]/10 text-[#ffb3b5] border border-[#ffb3b5]/20 rounded text-[10px] font-bold font-label uppercase tracking-widest hover:bg-[#ffb3b5]/20 transition-all"
              >
                  Re-Auth UI
              </button>
          </div>
        </div>
      </motion.div>
    );
  }

// ─── GitHub Card (Connected/Prompt) ───────────────────────────────────────

function GitHubCard({ initialStatus, config, onFinish }: { initialStatus: GitHubStatus; config: ServiceConfig; onFinish: (s: string) => void }) {
  const [status, setStatus] = useState<GitHubStatus>(initialStatus);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setStatus(initialStatus);
  }, [initialStatus]);

  const handleConnect = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/github`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'GitHub OAuth setup is incomplete.');
      }
      const { authorization_url } = await res.json();
      const popup = openCenterPopup(authorization_url, 'GitHub Integration', 600, 700);
      const interval = setInterval(() => {
        if (!popup || popup.closed) {
          clearInterval(interval);
          setLoading(false);
          onFinish('check');
        }
      }, 1000);
    } catch (e: any) {
      setError(e.message || 'Check your .env configuration.');
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/connections/github`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to disconnect.');
      setStatus({ connected: false });
    } catch (e: any) {
      setError(e.message || 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div layout className="bg-[#161616] border border-[#232323] rounded-lg overflow-hidden group hover:border-[#ffb3b5]/20 transition-all">
      <div className="flex items-center justify-between px-6 py-5 border-b border-[#232323]">
        <div className="flex items-center gap-4">
          <div className="relative flex items-center justify-center w-11 h-11 rounded-lg bg-[#1c1b1b] border border-[#2a2a2a]">
            <svg viewBox="0 0 24 24" className="w-6 h-6 fill-[#c9c9c9]" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
            </svg>
          </div>
          <div>
            <p className="font-headline text-white text-base font-bold">GitHub Account</p>
            <p className="font-body text-[#6b6b6b] text-xs mt-0.5">Direct OAuth connection to your personal repository context</p>
          </div>
        </div>

        <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-[11px] font-label font-bold uppercase tracking-widest ${
          status.connected ? 'border-emerald-900/60 bg-emerald-950/40 text-emerald-400' : 'border-[#2a2a2a] bg-[#1c1b1b] text-[#555]'
        }`}>
          <span className={`h-1.5 w-1.5 rounded-full ${status.connected ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]' : 'bg-[#444]'}`} />
          {status.connected ? 'Connected' : 'Ready'}
        </div>
      </div>

      <div className="px-6 py-5">
        <AnimatePresence mode="wait">
          {status.connected ? (
            <motion.div key="connected" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {status.avatar_url && <img src={status.avatar_url} className="w-10 h-10 rounded-full border-2 border-[#2a2a2a] ring-1 ring-[#ffb3b5]/20" />}
                <div>
                  <p className="font-headline text-white font-bold text-sm">@{status.username}</p>
                  <p className="font-body text-[#555] text-xs mt-0.5">{formatDate(status.connected_at)}</p>
                </div>
              </div>
              <button disabled={loading} onClick={handleDisconnect} className="flex items-center gap-2 px-4 py-2 text-xs font-bold font-label uppercase tracking-widest text-[#a38b88] border border-[#2a2a2a] rounded hover:border-[#4A0404] hover:text-[#ffb3b5] hover:bg-[#4A0404]/10 transition-all disabled:opacity-20">
                <span className="material-symbols-outlined text-base">link_off</span>
                Unlink account
              </button>
            </motion.div>
          ) : (
            <motion.div key="disconnected" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-4">
              {config.configured ? (
                <div className="flex items-center justify-between">
                  <p className="font-body text-[#6b6b6b] text-sm leading-relaxed max-w-md">The secure handshake is ready. Use the button to initiate the GitHub permissions prompt.</p>
                  <button
                    disabled={loading}
                    onClick={handleConnect}
                    className="flex items-center gap-3 px-6 py-3 text-xs font-bold font-label uppercase tracking-widest bg-[#ffb3b5] text-[#131313] border border-[#ffb3b5]/20 rounded hover:scale-[1.02] active:scale-[0.98] transition-all"
                  >
                    <span className="material-symbols-outlined text-base font-black">login</span>
                    Connect account
                  </button>
                </div>
              ) : (
                <GitHubSetupGuide />
              )}
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {error && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="mt-4 flex items-center gap-3 px-4 py-3 bg-[#4A0404]/20 border border-[#4A0404]/40 rounded text-[#ffb3b5] text-xs font-body">
              <span className="material-symbols-outlined text-base">warning</span>
              {error}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

function SlackFamigliaWizard({ onFinish }: { onFinish: () => void }) {
  const [step, setStep] = useState(1);
  const [appLevelToken, setAppLevelToken] = useState('');
  const [provisionedApps, setProvisionedApps] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('');

  const handleProvision = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/connections/slack/provision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_level_token: appLevelToken }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Provisioning failed');
      
      setProvisionedApps(data.apps);
      setStep(2);
      if (data.apps.length > 0) setActiveTab(data.apps[0].agent_id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const [tokens, setTokens] = useState<Record<string, { bot: string; app: string }>>({});

  const handleFinalize = async (agentId: string) => {
    const t = tokens[agentId];
    if (!t || !t.bot || !t.app) {
        setError('Both Bot and Socket tokens are required.');
        return;
    }
    setLoading(true);
    try {
        const res = await fetch(`${API_BASE}/connections/slack/finalize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agent_id: agentId,
                bot_token: t.bot,
                app_token: t.app
            }),
        });
        if (!res.ok) throw new Error('Failed to save tokens');
        onFinish();
    } catch (e: any) {
        setError(e.message);
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {step === 1 && (
        <motion.div 
          initial={{ opacity: 0, scale: 0.98 }} 
          animate={{ opacity: 1, scale: 1 }} 
          className="p-10 bg-white/5 backdrop-blur-2xl border border-white/10 rounded-2xl space-y-8 shadow-[0_30px_60px_rgba(0,0,0,0.4)] relative overflow-hidden"
        >
          {/* Decorative Gradient Glow */}
          <div className="absolute -top-24 -right-24 w-64 h-64 bg-[#ffb3b5]/10 rounded-full blur-[100px] pointer-events-none" />
          
          <div className="flex items-center gap-6 relative z-10">
            <div className="p-5 bg-gradient-to-br from-[#4A0404] to-[#131313] rounded-2xl border border-white/20 shadow-[0_0_30px_rgba(74,4,4,0.3)]">
              <span className="material-symbols-outlined text-[#ffb3b5] text-4xl">hail</span>
            </div>
            <div>
              <h3 className="text-3xl font-headline font-black text-white tracking-tighter uppercase italic">Assemble the Famiglia</h3>
              <p className="text-sm font-body text-[#a38b88] mt-2 leading-relaxed opacity-80">
                Don Jimmy, let's manifest the multi-bot network. A single <strong>App-Level Token</strong> triggers the birth of your digital empire.
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-5 relative z-10">
            <div className="space-y-2">
                <label className="text-[10px] font-label font-bold text-[#ffb3b5]/60 uppercase tracking-[0.3em] ml-1">Bootstrap Token</label>
                <input
                  type="password"
                  placeholder="xapp-1-A123..."
                  value={appLevelToken}
                  onChange={e => setAppLevelToken(e.target.value)}
                  className="w-full bg-[#0d0d0d]/80 border border-white/5 rounded-xl px-6 py-4 text-sm font-mono text-white placeholder-[#333] focus:outline-none focus:ring-2 focus:ring-[#ffb3b5]/30 focus:border-[#ffb3b5]/40 transition-all shadow-inner"
                />
            </div>
            <button
               onClick={handleProvision}
               disabled={loading || !appLevelToken}
               className="group relative w-full py-5 bg-gradient-to-r from-[#ffb3b5] to-[#f472b6] text-[#131313] font-black font-label uppercase tracking-[0.2em] rounded-xl overflow-hidden shadow-[0_10px_30px_rgba(255,179,181,0.2)] hover:shadow-[0_15px_40px_rgba(255,179,181,0.4)] transition-all disabled:opacity-30 active:scale-[0.98]"
            >
              <span className="relative z-10 flex items-center justify-center gap-3">
                {loading ? (
                    <span className="material-symbols-outlined animate-spin">sync</span>
                ) : (
                    <span className="material-symbols-outlined group-hover:rotate-12 transition-transform">bolt</span>
                )}
                Initialize Global Network
              </span>
              <div className="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          </div>
          
          <div className="p-5 bg-white/[0.02] rounded-xl border border-white/5 relative z-10">
            <p className="text-[10px] font-label font-black text-[#555] uppercase tracking-[0.1em] mb-3 flex items-center gap-2">
                <span className="material-symbols-outlined text-xs bg-[#ffb3b5]/10 p-1 rounded">school</span> 
                Provisioning Protocol
            </p>
            <p className="text-[11px] font-body text-[#7f7f7f] leading-relaxed">
                Ensure your app at <code className="text-[#ffb3b5]/60">api.slack.com</code> has the <strong className="text-white">apps.manifest:write</strong> scope enabled under App-Level Tokens. This allows Famiglia Core to auto-generate all 8 agents instantly.
            </p>
          </div>
        </motion.div>
      )}

      {step === 2 && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
            <div className="flex items-center justify-between px-2">
                <h4 className="text-xl font-headline font-bold text-white tracking-tight">Agent Authorization Portal</h4>
                <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-950/20 border border-emerald-900/30 rounded-full">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"/>
                    <span className="text-[10px] font-label font-bold uppercase text-emerald-400 tracking-widest">Manifests Deployed</span>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                {provisionedApps.map(app => (
                    <button
                        key={app.agent_id}
                        onClick={() => setActiveTab(app.agent_id)}
                        className={`px-4 py-3 rounded-lg border text-xs font-label uppercase tracking-widest font-bold transition-all ${
                            activeTab === app.agent_id 
                            ? 'bg-[#ffb3b5] text-[#131313] border-[#ffb3b5]' 
                            : 'bg-[#161616] text-[#444] border-[#232323] hover:border-[#444]'
                        }`}
                    >
                        {app.name}
                    </button>
                ))}
            </div>

            <AnimatePresence mode="wait">
                {provisionedApps.map(app => (
                    activeTab === app.agent_id && (
                        <motion.div
                            key={app.agent_id}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 10 }}
                            className="bg-[#161616] border border-[#232323] rounded-xl p-8 space-y-6 shadow-2xl"
                        >
                            <div className="flex items-start justify-between">
                                <div className="space-y-1">
                                    <h5 className="text-2xl font-headline font-black text-white">{app.name} Configuration</h5>
                                    <p className="text-xs font-body text-[#555]">App ID: <code className="text-[#a38b88]">{app.app_id}</code></p>
                                </div>
                                <a
                                    href={app.install_url}
                                    target="_blank"
                                    className="flex items-center gap-3 px-6 py-3 bg-white text-black text-xs font-black font-label uppercase tracking-widest rounded hover:bg-[#ffb3b5] transition-all shadow-[0_4px_20px_rgba(255,179,181,0.1)]"
                                >
                                    <span className="material-symbols-outlined text-base">install_desktop</span>
                                    Install App
                                </a>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-3">
                                    <label className="text-[10px] font-label font-bold text-[#888] uppercase tracking-widest">Bot User OAuth Token</label>
                                    <div className="relative">
                                        <input
                                            type="password"
                                            placeholder="xoxb-..."
                                            value={tokens[app.agent_id]?.bot || ''}
                                            onChange={e => setTokens({ ...tokens, [app.agent_id]: { ...tokens[app.agent_id], bot: e.target.value } })}
                                            className="w-full bg-[#0d0d0d] border border-[#232323] rounded px-4 py-3 text-sm font-mono text-[#ffb3b5] focus:outline-none focus:border-[#ffb3b5]/40"
                                        />
                                        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[9px] font-label font-black text-[#2a2a2a] uppercase">Identity</span>
                                    </div>
                                    <p className="text-[10px] font-body text-[#444]">Found in <strong>OAuth & Permissions</strong> after installation.</p>
                                </div>
                                <div className="space-y-3">
                                    <label className="text-[10px] font-label font-bold text-[#888] uppercase tracking-widest">App-Level Socket Token</label>
                                    <div className="relative">
                                        <input
                                            type="password"
                                            placeholder="xapp-..."
                                            value={tokens[app.agent_id]?.app || ''}
                                            onChange={e => setTokens({ ...tokens, [app.agent_id]: { ...tokens[app.agent_id], app: e.target.value } })}
                                            className="w-full bg-[#0d0d0d] border border-[#232323] rounded px-4 py-3 text-sm font-mono text-[#ffb3b5] focus:outline-none focus:border-[#ffb3b5]/40"
                                        />
                                        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[9px] font-label font-black text-[#2a2a2a] uppercase">Stream</span>
                                    </div>
                                    <p className="text-[10px] font-body text-[#444]">Found in <strong>Basic Information</strong> → App-Level Tokens.</p>
                                </div>
                            </div>

                            <button
                                onClick={() => handleFinalize(app.agent_id)}
                                disabled={loading || !tokens[app.agent_id]?.bot || !tokens[app.agent_id]?.app}
                                className="w-full py-4 border border-[#ffb3b5]/20 text-[#ffb3b5] text-xs font-bold font-label uppercase tracking-widest rounded hover:bg-[#ffb3b5]/5 transition-all"
                            >
                                Secure {app.name}'s Connection
                            </button>
                        </motion.div>
                    )
                ))}
            </AnimatePresence>
        </motion.div>
      )}

      {error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-4 bg-[#4A0404]/30 border border-[#4A0404] rounded text-[#ff1a1a] text-xs font-body flex items-center gap-3">
            <span className="material-symbols-outlined text-base">error</span>
            {error}
        </motion.div>
      )}
    </div>
  );
}

function SlackCard({ initialStatus, config, onFinish }: { initialStatus: SlackStatus; config: SlackConfig, onFinish: () => void }) {
  const [famigliaStatus, setFamigliaStatus] = useState<Record<string, any>>({});
  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    fetchFamigliaStatus();
  }, [initialStatus]);

  const fetchFamigliaStatus = async () => {
    try {
        const res = await fetch(`${API_BASE}/connections/slack/status`);
        if (res.ok) setFamigliaStatus(await res.json());
    } catch (e) {}
  };

  const handleDisconnect = async () => {
    try {
      const res = await fetch(`${API_BASE}/connections/slack`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to disconnect.');
      fetchFamigliaStatus();
      onFinish();
    } catch (e: any) {
      console.error(e.message || 'Unknown error');
    }
  };

  const allConnected = Object.values(famigliaStatus).every(s => s.connected) && Object.keys(famigliaStatus).length > 0;

  return (
    <motion.div layout className="bg-[#161616] border border-[#232323] rounded-lg overflow-hidden group hover:border-[#ffb3b5]/20 transition-all">
      <div className="flex items-center justify-between px-6 py-5 border-b border-[#232323]">
        <div className="flex items-center gap-4">
          <div className="relative flex items-center justify-center w-11 h-11 rounded-lg bg-[#1c1b1b] border border-[#2a2a2a]">
            <svg viewBox="0 0 122.8 122.8" className="w-6 h-6" xmlns="http://www.w3.org/2000/svg">
              <path d="M25.8 77.6c0 7.1-5.8 12.9-12.9 12.9S0 84.7 0 77.6s5.8-12.9 12.9-12.9h12.9v12.9zm6.4 0c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9v32.3c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V77.6z" fill="#E01E5A"/><path d="M45.1 25.8c-7.1 0-12.9-5.8-12.9-12.9S38 0 45.1 0s12.9 5.8 12.9 12.9v12.9H45.1zm0 6.4c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H12.9C5.8 58.1 0 52.3 0 45.1s5.8-12.9 12.9-12.9h32.2z" fill="#36C5F0"/><path d="M97 45.1c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9-5.8 12.9-12.9 12.9H97V45.1zm-6.4 0c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V12.9C77.6 5.8 83.4 0 90.5 0s12.9 5.8 12.9 12.9v32.2z" fill="#2EB67D"/><path d="M77.6 97c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9-12.9-5.8-12.9-12.9V97h12.9zm0-6.4c-7.1 0-12.9-5.8-12.9-12.9s5.8-12.9 12.9-12.9h32.3c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H77.6z" fill="#ECB22E"/>
            </svg>
          </div>
          <div>
            <p className="font-headline text-white text-base font-bold">Slack Famiglia</p>
            <p className="font-body text-[#6b6b6b] text-xs mt-0.5">Multi-bot network for high-vibe executive assistance</p>
          </div>
        </div>

        <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-[11px] font-label font-bold uppercase tracking-widest ${
          allConnected ? 'border-emerald-900/60 bg-emerald-950/40 text-emerald-400' : 'border-[#2a2a2a] bg-[#1c1b1b] text-[#555]'
        }`}>
          <span className={`h-1.5 w-1.5 rounded-full ${allConnected ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]' : 'bg-[#444]'}`} />
          {allConnected ? 'Full Family Online' : 'Awaiting Orders'}
        </div>
      </div>

      <div className="px-6 py-5">
        <AnimatePresence mode="wait">
          {showWizard ? (
             <SlackFamigliaWizard onFinish={() => { fetchFamigliaStatus(); setShowWizard(false); }} />
          ) : (
            <div className="space-y-4">
                <div className="grid grid-cols-4 md:grid-cols-7 gap-2">
                    {Object.entries(famigliaStatus).map(([id, s]) => (
                        <div key={id} className={`flex flex-col items-center gap-2 p-2 rounded border transition-all ${s.connected ? 'border-emerald-950 bg-emerald-950/20' : 'border-[#232323] grayscale opacity-40'}`}>
                            <div className="text-xl">{AGENT_EMOJIS[id as keyof typeof AGENT_EMOJIS]}</div>
                            <span className="text-[8px] font-label font-bold uppercase tracking-tighter text-[#888]">{id}</span>
                        </div>
                    ))}
                </div>

                <div className="flex items-center justify-between border-t border-[#232323] pt-4">
                   <p className="font-body text-[#6b6b6b] text-sm leading-relaxed max-w-sm">
                        {allConnected ? 'All agents have been provisioned and secured. The famiglia is ready for directives.' : 'The family needs assembly. Enter the secure portal to provision your agent bots.'}
                   </p>
                   {allConnected ? (
                       <button onClick={handleDisconnect} className="text-[10px] font-label font-bold uppercase text-[#4A0404] hover:text-[#ff1a1a]">Purge credentials</button>
                   ) : (
                       <button
                         onClick={() => setShowWizard(true)}
                         className="flex items-center gap-3 px-6 py-3 text-xs font-bold font-label uppercase tracking-widest bg-[#122e23] text-[#42d392] border border-[#42d392]/20 rounded hover:scale-[1.02] active:scale-[0.98] transition-all"
                       >
                         <span className="material-symbols-outlined text-base font-black">bolt</span>
                         Assemble the Family
                       </button>
                   )}
                </div>
            </div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

const AGENT_EMOJIS = {
    alfredo: "🎩",
    vito: "🦅",
    riccardo: "🔧",
    rossini: "🔬",
    tommy: "🔫",
    bella: "💋",
    kowalski: "📊"
};
// ─── Notion Card (Connected/Prompt) ────────────────────────────────────────

function NotionCard({ initialStatus, config, onFinish }: { initialStatus: NotionStatus; config: ServiceConfig; onFinish: (s: string) => void }) {
    const [status, setStatus] = useState<NotionStatus>(initialStatus);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
  
    const handleConnect = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/auth/notion`);
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || 'Notion OAuth setup is incomplete.');
        }
        const { authorization_url } = await res.json();
        const popup = openCenterPopup(authorization_url, 'Notion Integration', 600, 700);
        const interval = setInterval(() => {
          if (!popup || popup.closed) {
            clearInterval(interval);
            setLoading(false);
            onFinish('check');
          }
        }, 1000);
      } catch (e: any) {
        setError(e.message || 'Check your .env configuration.');
        setLoading(false);
      }
    };
  
    const handleDisconnect = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/connections/notion`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to disconnect.');
        setStatus({ connected: false });
      } catch (e: any) {
        setError(e.message || 'Unknown error');
      } finally {
        setLoading(false);
      }
    };
  
    return (
      <motion.div layout className="bg-[#161616] border border-[#232323] rounded-lg overflow-hidden group hover:border-[#ffb3b5]/20 transition-all">
        <div className="flex items-center justify-between px-6 py-5 border-b border-[#232323]">
          <div className="flex items-center gap-4">
            <div className="relative flex items-center justify-center w-11 h-11 rounded-lg bg-[#1c1b1b] border border-[#2a2a2a]">
              <span className="material-symbols-outlined text-[#c9c9c9] text-2xl">description</span>
            </div>
            <div>
              <p className="font-headline text-white text-base font-bold">Notion Workspace</p>
              <p className="font-body text-[#6b6b6b] text-xs mt-0.5">Secure gateway to your connected Notion knowledge base</p>
            </div>
          </div>
  
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-[11px] font-label font-bold uppercase tracking-widest ${
            status.connected ? 'border-emerald-900/60 bg-emerald-950/40 text-emerald-400' : 'border-[#2a2a2a] bg-[#1c1b1b] text-[#555]'
          }`}>
            <span className={`h-1.5 w-1.5 rounded-full ${status.connected ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]' : 'bg-[#444]'}`} />
            {status.connected ? 'Linked' : 'Ready'}
          </div>
        </div>
  
        <div className="px-6 py-5">
          <AnimatePresence mode="wait">
            {status.connected ? (
              <motion.div key="connected" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {status.avatar_url ? (
                      <img src={status.avatar_url} className="w-10 h-10 rounded border border-[#2a2a2a] ring-1 ring-[#ffb3b5]/10" />
                  ) : (
                    <div className="w-10 h-10 rounded bg-[#1c1b1b] border border-[#2a2a2a] flex items-center justify-center">
                        <span className="material-symbols-outlined text-[#444] text-xl">workspaces</span>
                    </div>
                  )}
                  <div>
                    <p className="font-headline text-white font-bold text-sm">{status.username}</p>
                    <p className="font-body text-[#555] text-xs mt-0.5">{formatDate(status.connected_at)}</p>
                  </div>
                </div>
                <button disabled={loading} onClick={handleDisconnect} className="flex items-center gap-2 px-4 py-2 text-xs font-bold font-label uppercase tracking-widest text-[#a38b88] border border-[#2a2a2a] rounded hover:border-[#4A0404] hover:text-[#ffb3b5] hover:bg-[#4A0404]/10 transition-all disabled:opacity-20">
                  <span className="material-symbols-outlined text-base">link_off</span>
                  Unlink Workspace
                </button>
              </motion.div>
            ) : (
              <motion.div key="disconnected" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-4">
                {config.configured ? (
                  <div className="flex items-center justify-between">
                    <p className="font-body text-[#6b6b6b] text-sm leading-relaxed max-w-md">The encryption tunnel is ready. Use the button to authorize access to your Notion workspace.</p>
                    <button
                      disabled={loading}
                      onClick={handleConnect}
                      className="flex items-center gap-3 px-6 py-3 text-xs font-bold font-label uppercase tracking-widest bg-[#ffb3b5] text-[#131313] border border-[#ffb3b5]/20 rounded hover:scale-[1.02] active:scale-[0.98] transition-all"
                    >
                      <span className="material-symbols-outlined text-base font-black">sync_alt</span>
                      Authorize Notion
                    </button>
                  </div>
                ) : (
                  <NotionSetupGuide />
                )}
              </motion.div>
            )}
          </AnimatePresence>
  
          <AnimatePresence>
            {error && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="mt-4 flex items-center gap-3 px-4 py-3 bg-[#4A0404]/20 border border-[#4A0404]/40 rounded text-[#ffb3b5] text-xs font-body">
                <span className="material-symbols-outlined text-base">warning</span>
                {error}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    );
  }

// ─── Ollama Card ─────────────────────────────────────────────────────────

type TestResult = { success: boolean; host?: string; models?: string[]; detail?: string } | null;

function OllamaCard({ initialStatus, onFinish }: { initialStatus: OllamaStatus; onFinish: () => void }) {
  const [status, setStatus] = useState<OllamaStatus>(initialStatus);
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { setStatus(initialStatus); }, [initialStatus]);

  const handleSave = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/connections/ollama/key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Failed to save API key.');
      }
      setApiKey('');
      onFinish();
    } catch (e: any) {
      setError(e.message || 'Unknown error.');
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    setError(null);
    setTestResult(null);
    try {
      const res = await fetch(`${API_BASE}/connections/ollama`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to disconnect.');
      setStatus({ connected: false });
      onFinish();
    } catch (e: any) {
      setError(e.message || 'Unknown error.');
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${API_BASE}/connections/ollama/test`);
      const body = await res.json();
      if (!res.ok) {
        setTestResult({ success: false, detail: body.detail || `Error ${res.status}` });
      } else {
        setTestResult({ success: true, host: body.host, models: body.models });
      }
    } catch {
      setTestResult({ success: false, detail: 'Could not reach the backend.' });
    } finally {
      setTesting(false);
    }
  };

  return (
    <motion.div layout className="bg-[#161616] border border-[#232323] rounded-lg overflow-hidden group hover:border-[#ffb3b5]/20 transition-all">
      <div className="flex items-center justify-between px-6 py-5 border-b border-[#232323]">
        <div className="flex items-center gap-4">
          <div className="relative flex items-center justify-center w-11 h-11 rounded-lg bg-[#1c1b1b] border border-[#2a2a2a]">
            <img src="/ollama.svg" alt="Ollama" className="w-7 h-7 object-contain" />
          </div>
          <div>
            <p className="font-headline text-white text-base font-bold">Ollama</p>
            <p className="font-body text-[#6b6b6b] text-xs mt-0.5">Local AI model runtime for private, on-device inference</p>
          </div>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-[11px] font-label font-bold uppercase tracking-widest ${
          status.connected ? 'border-emerald-900/60 bg-emerald-950/40 text-emerald-400' : 'border-[#2a2a2a] bg-[#1c1b1b] text-[#555]'
        }`}>
          <span className={`h-1.5 w-1.5 rounded-full ${status.connected ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]' : 'bg-[#444]'}`} />
          {status.connected ? 'Connected' : 'Ready'}
        </div>
      </div>

      <div className="px-6 py-5">
        <AnimatePresence mode="wait">
          {status.connected ? (
            <motion.div key="connected" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-headline text-white font-bold text-sm">API Key stored</p>
                  <p className="font-body text-[#555] text-xs mt-0.5">{formatDate(status.connected_at)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    disabled={testing || loading}
                    onClick={handleTest}
                    className="flex items-center gap-2 px-4 py-2 text-xs font-bold font-label uppercase tracking-widest text-[#6b9e8a] border border-[#1e3a30] rounded hover:border-emerald-800 hover:text-emerald-400 hover:bg-emerald-950/30 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    <span className={`material-symbols-outlined text-base ${testing ? 'animate-spin' : ''}`}>{testing ? 'progress_activity' : 'network_check'}</span>
                    {testing ? 'Testing…' : 'Test connection'}
                  </button>
                  <button
                    disabled={loading}
                    onClick={handleDisconnect}
                    className="flex items-center gap-2 px-4 py-2 text-xs font-bold font-label uppercase tracking-widest text-[#a38b88] border border-[#2a2a2a] rounded hover:border-[#4A0404] hover:text-[#ffb3b5] hover:bg-[#4A0404]/10 transition-all disabled:opacity-20"
                  >
                    <span className="material-symbols-outlined text-base">link_off</span>
                    Remove key
                  </button>
                </div>
              </div>

              <AnimatePresence>
                {testResult && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className={`px-4 py-3 rounded border text-xs font-body flex flex-col gap-1.5 ${
                      testResult.success
                        ? 'bg-emerald-950/30 border-emerald-900/50 text-emerald-400'
                        : 'bg-[#4A0404]/20 border-[#4A0404]/40 text-[#ffb3b5]'
                    }`}
                  >
                    <div className="flex items-center gap-2 font-bold">
                      <span className="material-symbols-outlined text-base">
                        {testResult.success ? 'check_circle' : 'error'}
                      </span>
                      {testResult.success
                        ? `Connected to ${testResult.host}`
                        : testResult.detail}
                    </div>
                    {testResult.success && testResult.models && testResult.models.length > 0 && (
                      <p className="text-emerald-600 pl-6">
                        Models available: {testResult.models.join(', ')}
                      </p>
                    )}
                    {testResult.success && testResult.models?.length === 0 && (
                      <p className="text-emerald-700 pl-6">No models pulled yet.</p>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ) : (
            <motion.div key="disconnected" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-4">
              <p className="font-body text-[#6b6b6b] text-sm leading-relaxed max-w-md">
                Enter your Ollama API key to enable authenticated access to your Ollama instance.
              </p>
              <div className="flex items-center gap-3">
                <div className="relative flex-1">
                  <input
                    type={showKey ? 'text' : 'password'}
                    value={apiKey}
                    onChange={e => setApiKey(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && apiKey.trim() && handleSave()}
                    placeholder="sk-••••••••••••••••"
                    className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded px-4 py-2.5 text-sm font-mono text-white placeholder-[#333] focus:outline-none focus:border-[#ffb3b5]/40 transition-all pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#444] hover:text-[#888] transition-colors"
                  >
                    <span className="material-symbols-outlined text-base">{showKey ? 'visibility_off' : 'visibility'}</span>
                  </button>
                </div>
                <button
                  disabled={loading || !apiKey.trim()}
                  onClick={handleSave}
                  className="flex items-center gap-2 px-5 py-2.5 text-xs font-bold font-label uppercase tracking-widest bg-[#ffb3b5] text-[#131313] rounded hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:scale-100"
                >
                  <span className="material-symbols-outlined text-base font-black">save</span>
                  Save key
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {error && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="mt-4 flex items-center gap-3 px-4 py-3 bg-[#4A0404]/20 border border-[#4A0404]/40 rounded text-[#ffb3b5] text-xs font-body">
              <span className="material-symbols-outlined text-base">warning</span>
              {error}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// ─── Main Connections View ────────────────────────────────────────────────

export function Connections({ successParam, errorParam, onClearParams }: any) {
  const [config, setConfig] = useState<Record<string, ServiceConfig>>({});
  const [githubStatus, setGithubStatus] = useState<GitHubStatus>({ connected: false });
  const [slackStatus, setSlackStatus] = useState<SlackStatus>({ connected: false });
  const [notionStatus, setNotionStatus] = useState<NotionStatus>({ connected: false });
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus>({ connected: false });
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ m: string; type: 'success' | 'error' } | null>(null);

  const fetchData = async () => {
    try {
      const [cfgRes, githubRes, slackRes, notionRes, ollamaRes] = await Promise.all([
        fetch(`${API_BASE}/connections/config`),
        fetch(`${API_BASE}/connections/github`),
        fetch(`${API_BASE}/connections/slack`),
        fetch(`${API_BASE}/connections/notion`),
        fetch(`${API_BASE}/connections/ollama`),
      ]);
      if (cfgRes.ok) setConfig(await cfgRes.json());
      if (githubRes.ok) setGithubStatus(await githubRes.json());
      if (slackRes.ok) setSlackStatus(await slackRes.json());
      if (notionRes.ok) setNotionStatus(await notionRes.json());
      if (ollamaRes.ok) setOllamaStatus(await ollamaRes.json());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Polling: Refresh data every 5 seconds to catch .env or status changes automatically
    const interval = setInterval(fetchData, 5000);

    // Listen for the 'github_success' or 'slack_success' signal from the popup window
    // Listen for OAuth signals from popup windows
    const handleMessage = (event: MessageEvent) => {
      if (event.data === 'github_success') {
        setToast({ m: 'Successfully linked GitHub account.', type: 'success' });
        fetchData();
      } else if (event.data === 'slack_success') {
        setToast({ m: 'Successfully established Slack workspace sync.', type: 'success' });
        fetchData();
      }
      if (event.data === 'notion_success') {
        setToast({ m: 'Successfully linked Notion workspace.', type: 'success' });
        fetchData();
      }
    };

    window.addEventListener('message', handleMessage);
    return () => {
      clearInterval(interval);
      window.removeEventListener('message', handleMessage);
    };
  }, []);

  useEffect(() => {
    if (successParam === 'true') {
      setToast({ m: 'Successfully linked service account.', type: 'success' });
      fetchData();
      onClearParams?.();
    } else if (errorParam) {
      setToast({ m: `Establishment error: ${errorParam}`, type: 'error' });
      onClearParams?.();
    }
  }, [successParam, errorParam]);

  if (loading) {
    return <div className="py-20 flex items-center justify-center text-[#ffb3b5] opacity-20"><span className="material-symbols-outlined animate-spin text-4xl">nest_remote_comfort_sensor</span></div>;
  }

  return (
    <div className="flex-1 flex flex-col gap-12 max-w-5xl mx-auto">
      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className={`fixed top-24 right-10 z-[100] px-6 py-4 rounded-lg shadow-2xl flex items-center gap-4 ${toast.type === 'success' ? 'bg-[#0d1f16] border border-emerald-900/50 text-emerald-400' : 'bg-[#1f0d0d] border border-red-900/50 text-red-400'}`}
          >
            <span className="material-symbols-outlined">{toast.type === 'success' ? 'verified_user' : 'report_problem'}</span>
            <span className="font-body text-sm font-medium">{toast.m}</span>
            <button onClick={() => setToast(null)}><span className="material-symbols-outlined text-sm opacity-40 hover:opacity-100 transition-all">close</span></button>
          </motion.div>
        )}
      </AnimatePresence>

      <header className="pb-2">
        <h1 className="text-5xl font-black font-headline text-white tracking-tighter">Gateway Portal</h1>
        <p className="font-body text-[#6b6b6b] mt-3 uppercase tracking-widest text-[10px] font-bold">Encrypted External Connections</p>
      </header>

      <div className="flex flex-col gap-10">

        {/* ── AI & LLMs ─────────────────────────────────────────────────── */}
        <section className="space-y-6">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-[#ffb3b5] text-base">smart_toy</span>
            <h2 className="text-xl font-headline font-bold text-white uppercase tracking-tighter">AI / LLMs</h2>
            <div className="h-px flex-1 bg-[#1c1b1b]" />
          </div>
          <OllamaCard
            initialStatus={ollamaStatus}
            onFinish={() => { fetchData(); setToast({ m: ollamaStatus.connected ? 'Ollama key removed.' : 'Ollama API key saved.', type: 'success' }); }}
          />
        </section>

        {/* ── Comms ─────────────────────────────────────────────────────── */}
        <section className="space-y-6">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-[#ffb3b5] text-base">forum</span>
            <h2 className="text-xl font-headline font-bold text-white uppercase tracking-tighter">Comms</h2>
            <div className="h-px flex-1 bg-[#1c1b1b]" />
          </div>
          <SlackCard
            initialStatus={slackStatus}
            config={config.slack || { configured: false, redirect_uri: '' }}
            onFinish={() => fetchData()}
          />
        </section>

        {/* ── Documentation ─────────────────────────────────────────────── */}
        <section className="space-y-6">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-[#ffb3b5] text-base">article</span>
            <h2 className="text-xl font-headline font-bold text-white uppercase tracking-tighter">Documentation</h2>
            <div className="h-px flex-1 bg-[#1c1b1b]" />
          </div>
          <div className="grid grid-cols-1 gap-6">
            <NotionCard
              initialStatus={notionStatus}
              config={config.notion || { configured: false, redirect_uri: '' }}
              onFinish={() => fetchData()}
            />
            <div className="bg-[#161616] border border-[#232323] p-6 rounded-lg flex items-center justify-between opacity-30 grayscale pointer-events-none">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-[#1c1b1b] border border-[#2a2a2a] rounded">
                  <span className="material-symbols-outlined text-[#444]">calendar_month</span>
                </div>
                <div>
                  <p className="font-headline font-bold text-white text-base">Google Core</p>
                  <p className="font-body text-[#6b6b6b] text-xs mt-0.5">Calendar and workspace services</p>
                </div>
              </div>
              <span className="px-3 py-1 bg-[#1c1b1b] border border-[#2a2a2a] text-[10px] font-label text-[#444] uppercase tracking-widest rounded">Restricted</span>
            </div>
          </div>
        </section>

        {/* ── Tech ──────────────────────────────────────────────────────── */}
        <section className="space-y-6">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-[#ffb3b5] text-base">code</span>
            <h2 className="text-xl font-headline font-bold text-white uppercase tracking-tighter">Tech</h2>
            <div className="h-px flex-1 bg-[#1c1b1b]" />
          </div>
          <GitHubCard
            initialStatus={githubStatus}
            config={config.github || { configured: false, redirect_uri: '' }}
            onFinish={() => fetchData()}
          />
        </section>

      </div>

      <footer className="mt-auto py-10 border-t border-[#1c1b1b] flex items-center justify-center">
        <p className="font-body text-[10px] text-[#333] uppercase tracking-[0.2em] font-bold text-center leading-relaxed">
            La Passione Inc. — Secured Terminal Access<br/>
            Personnel-Specific Integration Portal
        </p>
      </footer>
    </div>
  );
}

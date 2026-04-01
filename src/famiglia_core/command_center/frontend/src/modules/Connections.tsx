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

function SlackSetupGuide() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-8 bg-[#0d0d0d] border border-[#ffb3b5]/10 rounded-xl space-y-6"
    >
      <div className="flex items-center gap-6">
        <div className="p-4 bg-[#041a4a]/30 rounded-xl border border-[#444]/50 shadow-[0_0_20px_rgba(4,26,74,0.2)]">
          <span className="material-symbols-outlined text-[#ffb3b5] text-4xl">settings_input_component</span>
        </div>
        <div>
          <h3 className="text-2xl font-headline font-bold text-white tracking-tighter">Slack Vault Integration Pending</h3>
          <p className="text-sm font-body text-[#6b6b6b] mt-1 leading-relaxed">
            Don Jimmy, your Slack OAuth credentials haven't been secured in the environment yet. 
            Add your <strong>App Client ID</strong> and <strong>Secret</strong> to the <code>.env</code> file, 
            then signal the backend to activate the secure channel.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-[#161616] border border-[#232323] rounded-lg space-y-2">
            <span className="text-[10px] font-label font-bold text-[#a38b88] uppercase tracking-widest">Step 1</span>
            <p className="text-[11px] font-body text-[#555] leading-relaxed">
                Add <code>SLACK_OAUTH_CLIENT_ID</code> and <code>SLACK_OAUTH_CLIENT_SECRET</code> to your <code>.env</code>.
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

function SlackCard({ initialStatus, config, onFinish }: { initialStatus: SlackStatus; config: SlackConfig; onFinish: (s: string) => void }) {
  const [status, setStatus] = useState<SlackStatus>(initialStatus);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setStatus(initialStatus);
  }, [initialStatus]);

  const handleConnect = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/slack`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Slack OAuth setup is incomplete.');
      }
      const { authorization_url } = await res.json();
      const popup = openCenterPopup(authorization_url, 'Slack Integration', 600, 700);
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
      const res = await fetch(`${API_BASE}/connections/slack`, { method: 'DELETE' });
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
            <svg viewBox="0 0 122.8 122.8" className="w-6 h-6" xmlns="http://www.w3.org/2000/svg">
              <path d="M25.8 77.6c0 7.1-5.8 12.9-12.9 12.9S0 84.7 0 77.6s5.8-12.9 12.9-12.9h12.9v12.9zm6.4 0c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9v32.3c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V77.6z" fill="#E01E5A"/><path d="M45.1 25.8c-7.1 0-12.9-5.8-12.9-12.9S38 0 45.1 0s12.9 5.8 12.9 12.9v12.9H45.1zm0 6.4c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H12.9C5.8 58.1 0 52.3 0 45.1s5.8-12.9 12.9-12.9h32.2z" fill="#36C5F0"/><path d="M97 45.1c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9-5.8 12.9-12.9 12.9H97V45.1zm-6.4 0c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V12.9C77.6 5.8 83.4 0 90.5 0s12.9 5.8 12.9 12.9v32.2z" fill="#2EB67D"/><path d="M77.6 97c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9-12.9-5.8-12.9-12.9V97h12.9zm0-6.4c-7.1 0-12.9-5.8-12.9-12.9s5.8-12.9 12.9-12.9h32.3c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H77.6z" fill="#ECB22E"/>
            </svg>
          </div>
          <div>
            <p className="font-headline text-white text-base font-bold">Slack Workspace</p>
            <p className="font-body text-[#6b6b6b] text-xs mt-0.5">Secure channel for identity-based team communications</p>
          </div>
        </div>

        <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-[11px] font-label font-bold uppercase tracking-widest ${
          status.connected ? 'border-emerald-900/60 bg-emerald-950/40 text-emerald-400' : 'border-[#2a2a2a] bg-[#1c1b1b] text-[#555]'
        }`}>
          <span className={`h-1.5 w-1.5 rounded-full ${status.connected ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]' : 'bg-[#444]'}`} />
          {status.connected ? 'Active Sync' : 'Offline'}
        </div>
      </div>

      <div className="px-6 py-5">
        <AnimatePresence mode="wait">
          {status.connected ? (
            <motion.div key="connected" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {status.avatar_url && <img src={status.avatar_url} className="w-10 h-10 rounded-lg border-2 border-[#2a2a2a] ring-1 ring-[#ffb3b5]/20" />}
                <div>
                  <p className="font-headline text-white font-bold text-sm">{status.username}</p>
                  <p className="font-body text-[#555] text-xs mt-0.5">{formatDate(status.connected_at)}</p>
                </div>
              </div>
              <button disabled={loading} onClick={handleDisconnect} className="flex items-center gap-2 px-4 py-2 text-xs font-bold font-label uppercase tracking-widest text-[#a38b88] border border-[#2a2a2a] rounded hover:border-[#4A0404] hover:text-[#ffb3b5] hover:bg-[#4A0404]/10 transition-all disabled:opacity-20">
                <span className="material-symbols-outlined text-base">leak_remove</span>
                Sever Connection
              </button>
            </motion.div>
          ) : (
            <motion.div key="disconnected" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-4">
              {config.configured ? (
                <div className="flex items-center justify-between">
                  <p className="font-body text-[#6b6b6b] text-sm leading-relaxed max-w-md">Encrypted handshake ready. Use the secure portal to authorize the Command Center in your workspace.</p>
                  <button
                    disabled={loading}
                    onClick={handleConnect}
                    className="flex items-center gap-3 px-6 py-3 text-xs font-bold font-label uppercase tracking-widest bg-[#122e23] text-[#42d392] border border-[#42d392]/20 rounded hover:scale-[1.02] active:scale-[0.98] transition-all"
                  >
                    <span className="material-symbols-outlined text-base font-black">sync_alt</span>
                    Initiate Sync
                  </button>
                </div>
              ) : (
                <SlackSetupGuide />
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

// ─── Main Connections View ────────────────────────────────────────────────

export function Connections({ successParam, errorParam, onClearParams }: any) {
  const [config, setConfig] = useState<Record<string, ServiceConfig>>({});
  const [githubStatus, setGithubStatus] = useState<GitHubStatus>({ connected: false });
  const [slackStatus, setSlackStatus] = useState<SlackStatus>({ connected: false });
  const [notionStatus, setNotionStatus] = useState<NotionStatus>({ connected: false });
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ m: string; type: 'success' | 'error' } | null>(null);

  const fetchData = async () => {
    try {
      const [cfgRes, githubRes, slackRes, notionRes] = await Promise.all([
        fetch(`${API_BASE}/connections/config`),
        fetch(`${API_BASE}/connections/github`),
        fetch(`${API_BASE}/connections/slack`),
        fetch(`${API_BASE}/connections/notion`),
      ]);
      if (cfgRes.ok) setConfig(await cfgRes.json());
      if (githubRes.ok) setGithubStatus(await githubRes.json());
      if (slackRes.ok) setSlackStatus(await slackRes.json());
      if (notionRes.ok) setNotionStatus(await notionRes.json());
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
        <section className="space-y-6">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-headline font-bold text-white uppercase tracking-tighter">Source Control Integration</h2>
            <div className="h-px flex-1 bg-[#1c1b1b]" />
          </div>
          <GitHubCard
            initialStatus={githubStatus}
            config={config.github || { configured: false, redirect_uri: '' }}
            onFinish={() => fetchData()}
          />
        </section>

        <section className="space-y-6">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-headline font-bold text-white uppercase tracking-tighter">Communication &amp; Identity</h2>
            <div className="h-px flex-1 bg-[#1c1b1b]" />
          </div>
          <SlackCard
            initialStatus={slackStatus}
            config={config.slack || { configured: false, redirect_uri: '' }}
            onFinish={() => fetchData()}
          />
        </section>

        <section className="space-y-6 opacity-40 grayscale pointer-events-none">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-headline font-bold text-white uppercase tracking-tighter">Protected Vaults</h2>
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
                  <p className="font-headline font-bold text-white text-base">Google Core</p>
                </div>
                <span className="px-3 py-1 bg-[#1c1b1b] border border-[#2a2a2a] text-[10px] font-label text-[#444] uppercase tracking-widest rounded">Restricted</span>
              </div>
          </div>
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

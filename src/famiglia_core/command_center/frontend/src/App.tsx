import { useState, useEffect, useCallback, useRef } from 'react';
import type { Agent, Action, Task, GraphDefinition, AppSettings } from './types';
import { TopNav } from './modules/ui/TopNav';
import { Sidebar } from './modules/ui/Sidebar';
import { SituationRoom } from './modules/SituationRoom';
import { SOP } from './modules/SOP';
import { Intelligences } from './modules/Intelligences';
import { Connections } from './modules/Connections';
import { Settings } from './modules/Settings';
import { DirectivesTerminal } from './modules/ui/DirectivesTerminal';
import { API_BASE } from './config';

const SETTINGS_STORAGE_KEY = 'command_center_settings';
const DEFAULT_SETTINGS: AppSettings = {
  honorific: 'Don',
  notificationsEnabled: true,
  backgroundAnimationsEnabled: true,
};

function getInitialSettings(): AppSettings {
  try {
    const raw = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<AppSettings>;
    return {
      honorific: parsed.honorific || DEFAULT_SETTINGS.honorific,
      notificationsEnabled:
        parsed.notificationsEnabled ?? DEFAULT_SETTINGS.notificationsEnabled,
      backgroundAnimationsEnabled:
        parsed.backgroundAnimationsEnabled ??
        DEFAULT_SETTINGS.backgroundAnimationsEnabled,
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function App() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [actions, setActions] = useState<Action[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [graphs, setGraphs] = useState<GraphDefinition[]>([]);
  const [selectedGraph, setSelectedGraph] = useState<GraphDefinition | null>(null);
  const [activeTab, setActiveTab] = useState('situation_room');
  const [settings, setSettings] = useState<AppSettings>(() => getInitialSettings());
  const [settingsHydrated, setSettingsHydrated] = useState(false);
  const hasSyncedSettings = useRef(false);

  // Read OAuth redirect params so Connections page can show a toast
  const params = new URLSearchParams(window.location.search);
  const [githubConnected, setGithubConnected] = useState<string | null>(params.get('github_connected'));
  const [githubError, setGithubError] = useState<string | null>(params.get('github_error'));

  // If we landed here via the OAuth callback tab param, switch to connections
  useEffect(() => {
    const tabParam = params.get('tab');
    if (tabParam) setActiveTab(tabParam);
  }, []);

  const clearOAuthParams = useCallback(() => {
    setGithubConnected(null);
    setGithubError(null);
    // Clean the URL without re-rendering
    window.history.replaceState({}, '', window.location.pathname);
  }, []);

  useEffect(() => {
    const hydrateSettings = async () => {
      try {
        const response = await fetch(`${API_BASE}/settings`);
        if (response.ok) {
          const backendSettings = (await response.json()) as AppSettings;
          setSettings({
            honorific: backendSettings.honorific || DEFAULT_SETTINGS.honorific,
            notificationsEnabled:
              backendSettings.notificationsEnabled ??
              DEFAULT_SETTINGS.notificationsEnabled,
            backgroundAnimationsEnabled:
              backendSettings.backgroundAnimationsEnabled ??
              DEFAULT_SETTINGS.backgroundAnimationsEnabled,
          });
        }
      } catch (error) {
        console.error('Failed to hydrate settings from backend, using local settings.', error);
      } finally {
        setSettingsHydrated(true);
      }
    };
    hydrateSettings();
  }, []);

  useEffect(() => {
    window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  }, [settings]);

  useEffect(() => {
    if (!settingsHydrated) return;

    // Skip first sync call after hydration to avoid writing unchanged values.
    if (!hasSyncedSettings.current) {
      hasSyncedSettings.current = true;
      return;
    }

    const sync = setTimeout(async () => {
      try {
        await fetch(`${API_BASE}/settings`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(settings),
        });
      } catch (error) {
        console.error('Failed to sync settings to backend.', error);
      }
    }, 250);

    return () => clearTimeout(sync);
  }, [settings, settingsHydrated]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [agentsRes, actionsRes, tasksRes] = await Promise.all([
          fetch(`${API_BASE}/agents`),
          fetch(`${API_BASE}/actions?limit=10`),
          fetch(`${API_BASE}/tasks?limit=3`)
        ]);
        
        if (agentsRes.ok) setAgents(await agentsRes.json());
        if (actionsRes.ok) setActions(await actionsRes.json());
        if (tasksRes.ok) setTasks(await tasksRes.json());
      } catch (err) {
        console.error("Failed to fetch data:", err);
      }
    };

    const fetchGraphs = async () => {
      try {
        const response = await fetch(`${API_BASE}/graphs`);
        const data = await response.json();
        setGraphs(data);
        if (data.length > 0 && !selectedGraph) {
          setSelectedGraph(data[0]);
        }
      } catch (error) {
        console.error("Failed to fetch graphs:", error);
      }
    };

    fetchData(); // Initial fetch for agents, actions, tasks
    fetchGraphs(); // Initial fetch for graphs

    const interval = setInterval(fetchData, 5000); // Set up interval for recurring data fetch
    return () => clearInterval(interval); // Cleanup interval on unmount
  }, [selectedGraph]);

  return (
    <div className="bg-background text-on-background font-body min-h-screen selection:bg-primary/30">
      <TopNav />
      <div className="flex">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        <main className="flex-1 ml-72 pt-16 relative overflow-hidden">
          {/* Background Map Overlay */}
          <div className="absolute inset-0 noir-bg-map pointer-events-none opacity-20"></div>
          
          <div className="relative z-10 p-10 max-w-7xl mx-auto space-y-10">
            {activeTab === 'situation_room' && (
              <SituationRoom 
                agents={agents} 
                actions={actions} 
                tasks={tasks} 
                honorific={settings.honorific}
              />
            )}
            {activeTab === 'sop' && (
              <SOP 
                graphs={graphs} 
                selectedGraph={selectedGraph} 
                setSelectedGraph={setSelectedGraph} 
              />
            )}
            {activeTab === 'intelligences' && (
              <Intelligences />
            )}
            {activeTab === 'connections' && (
              <Connections
                successParam={githubConnected}
                errorParam={githubError}
                onClearParams={clearOAuthParams}
              />
            )}
            {activeTab === 'settings' && (
              <Settings settings={settings} onSettingsChange={setSettings} />
            )}
            {/* Fallback for other tabs */}
            {!['situation_room', 'sop', 'intelligences', 'connections', 'settings'].includes(activeTab) && (
              <div className="flex flex-col items-center justify-center py-40 opacity-40">
                <span className="material-symbols-outlined text-6xl mb-4">construction</span>
                <p className="font-headline text-2xl uppercase tracking-widest text-[#a38b88]">Under Construction</p>
                <p className="font-body text-sm mt-2 uppercase tracking-tighter text-outline">Section Restricted to Consigliere Level</p>
              </div>
            )}
          </div>
        </main>
      </div>
      <DirectivesTerminal />
      <div className="fixed left-72 top-16 w-[1px] h-full bg-[#1c1b1b] z-30"></div>
    </div>
  );
}

export default App;

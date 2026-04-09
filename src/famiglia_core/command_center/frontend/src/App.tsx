import { useState, useEffect, useCallback, useRef } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import type {
  Agent,
  Task,
  RecurringTask,
  GraphDefinition,
  AppSettings,
  PaginatedTasks,
  PaginatedActions,
  ActionLog,
} from './types';
import { TopNav } from './modules/ui/TopNav';
import { Sidebar } from './modules/ui/Sidebar';
import { Agenda } from './modules/Agenda';
import { SituationRoom } from './modules/SituationRoom';
import { Operations } from './modules/Operations';
import { Settings } from './modules/Settings';
import { Famiglia } from './modules/Famiglia';
import { Terminal } from './modules/Terminal';
import { DirectivesTerminal } from './modules/ui/DirectivesTerminal';
import { TerminalProvider } from './modules/TerminalContext';
import { ToastProvider } from './modules/ui/ToastProvider';
import { DirectiveModal } from './modules/ui/DirectiveModal';
import { API_BASE } from './config';

const SETTINGS_STORAGE_KEY = 'command_center_settings';
const DEFAULT_SETTINGS: AppSettings = {
  honorific: 'Don',
  famigliaName: 'The Family',
  notificationsEnabled: true,
  backgroundAnimationsEnabled: true,
  personalDirective: '',
  systemPrompt: '',
};

function getInitialSettings(): AppSettings {
  try {
    const raw = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<AppSettings>;
    return {
      honorific: parsed.honorific || DEFAULT_SETTINGS.honorific,
      famigliaName: parsed.famigliaName || DEFAULT_SETTINGS.famigliaName,
      notificationsEnabled:
        parsed.notificationsEnabled ?? DEFAULT_SETTINGS.notificationsEnabled,
      backgroundAnimationsEnabled:
        parsed.backgroundAnimationsEnabled ??
        DEFAULT_SETTINGS.backgroundAnimationsEnabled,
      personalDirective: parsed.personalDirective || DEFAULT_SETTINGS.personalDirective,
      systemPrompt: parsed.systemPrompt || DEFAULT_SETTINGS.systemPrompt,
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function App() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [actions, setActions] = useState<ActionLog[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [recurringTasks, setRecurringTasks] = useState<RecurringTask[]>([]);
  const [graphs, setGraphs] = useState<GraphDefinition[]>([]);
  const [selectedGraph, setSelectedGraph] = useState<GraphDefinition | null>(null);
  const [settings, setSettings] = useState<AppSettings>(() => getInitialSettings());
  const [isDirectiveModalOpen, setDirectiveModalOpen] = useState(false);
  const [settingsHydrated, setSettingsHydrated] = useState(false);
  const hasSyncedSettings = useRef(false);

  // Read OAuth redirect params so Connections page can show a toast
  const params = new URLSearchParams(window.location.search);
  const [githubConnected, setGithubConnected] = useState<string | null>(params.get('github_connected'));
  const [githubError, setGithubError] = useState<string | null>(params.get('github_error'));

  // If we landed here via the OAuth callback tab param, switch to connections
  useEffect(() => {
    const tabParam = params.get('tab');
    if (tabParam) {
      navigate(`/${tabParam}`, { replace: true });
    }
  }, [navigate, params]);

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
            famigliaName: backendSettings.famigliaName || DEFAULT_SETTINGS.famigliaName,
            notificationsEnabled:
              backendSettings.notificationsEnabled ??
              DEFAULT_SETTINGS.notificationsEnabled,
            backgroundAnimationsEnabled:
              backendSettings.backgroundAnimationsEnabled ??
              DEFAULT_SETTINGS.backgroundAnimationsEnabled,
            personalDirective: backendSettings.personalDirective || DEFAULT_SETTINGS.personalDirective,
            systemPrompt: backendSettings.systemPrompt || DEFAULT_SETTINGS.systemPrompt,
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
        const [agentsRes, actionsRes, tasksRes, recurringTasksRes] = await Promise.all([
          fetch(`${API_BASE}/agents`),
          fetch(`${API_BASE}/actions?limit=24`),
          fetch(`${API_BASE}/tasks?limit=40`),
          fetch(`${API_BASE}/recurring-tasks`)
        ]);
        
        if (agentsRes.ok) {
          const data = await agentsRes.json();
          setAgents(Array.isArray(data) ? data : []);
        }
        if (actionsRes.ok) {
          const data = await actionsRes.json() as PaginatedActions;
          setActions(Array.isArray(data.actions) ? data.actions : []);
        }
        if (tasksRes.ok) {
          const data = await tasksRes.json() as PaginatedTasks;
          setTasks(Array.isArray(data.tasks) ? data.tasks : []);
        }
        if (recurringTasksRes.ok) {
          const data = await recurringTasksRes.json();
          setRecurringTasks(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        console.error("Failed to fetch data:", err);
      }
    };

    const fetchGraphs = async () => {
      try {
        const response = await fetch(`${API_BASE}/operations/graphs`);
        if (response.ok) {
          const data = await response.json();
          const validGraphs = Array.isArray(data) ? data : [];
          setGraphs(validGraphs);
          if (validGraphs.length > 0 && !selectedGraph) {
            setSelectedGraph(validGraphs[0]);
          }
        } else {
          setGraphs([]);
        }
      } catch (error) {
        console.error("Failed to fetch graphs:", error);
        setGraphs([]);
      }
    };

    fetchData(); // Initial fetch for agents, actions, tasks
    fetchGraphs(); // Initial fetch for graphs

    const interval = setInterval(fetchData, 5000); // Set up interval for recurring data fetch
    return () => clearInterval(interval); // Cleanup interval on unmount
  }, [selectedGraph]);

  return (
    <ToastProvider>
      <TerminalProvider>
        <div className="bg-background text-on-background font-body min-h-screen selection:bg-primary/30">
        <TopNav />
        <div className="flex">
          <Sidebar famigliaName={settings.famigliaName} />
          <main className="flex-1 ml-72 h-screen pt-16 relative overflow-hidden">
            {/* Background Map Overlay */}
            <div className="absolute inset-0 noir-bg-map pointer-events-none opacity-20"></div>
            
            <div className="relative z-10 p-10 max-w-7xl mx-auto space-y-10">
              <Routes>
                <Route path="/" element={<Navigate to="/situation_room" replace />} />
                <Route 
                  path="/agenda" 
                  element={
                    <Agenda
                      agents={agents}
                      actions={actions}
                      tasks={tasks}
                      recurringTasks={recurringTasks}
                      honorific={settings.honorific}
                    />
                  } 
                />
                <Route 
                  path="/situation_room" 
                  element={
                    <SituationRoom 
                      actions={actions} 
                      tasks={tasks} 
                      graphs={graphs}
                      honorific={settings.honorific}
                      onExecuteDirective={() => setDirectiveModalOpen(true)}
                    />
                  } 
                />
                <Route 
                  path="/operations" 
                  element={
                    <Operations 
                      graphs={graphs} 
                      selectedGraph={selectedGraph} 
                      setSelectedGraph={setSelectedGraph} 
                      initialTasks={tasks}
                    />
                  } 
                />
                <Route path="/famiglia" element={<Famiglia />} />
                <Route path="/terminal" element={<Terminal />} />
                <Route 
                  path="/settings" 
                  element={
                    <Settings 
                      settings={settings} 
                      onSettingsChange={setSettings} 
                      githubConnected={githubConnected}
                      githubError={githubError}
                      onClearOAuthParams={clearOAuthParams}
                    />
                  } 
                />
                <Route 
                  path="*" 
                  element={
                    <div className="flex flex-col items-center justify-center py-40 opacity-40">
                      <span className="material-symbols-outlined text-6xl mb-4">construction</span>
                      <p className="font-headline text-2xl uppercase tracking-widest text-[#a38b88]">Under Construction</p>
                      <p className="font-body text-sm mt-2 uppercase tracking-tighter text-outline">Section Restricted to Consigliere Level</p>
                    </div>
                  } 
                />
              </Routes>
            </div>
          </main>
        </div>
        <DirectivesTerminal />
        <DirectiveModal 
          isOpen={isDirectiveModalOpen} 
          onClose={() => setDirectiveModalOpen(false)} 
          graphs={graphs}
        />
        <div className="fixed left-72 top-16 w-[1px] h-full bg-[#1c1b1b] z-30"></div>
      </div>
      </TerminalProvider>
    </ToastProvider>
  );
}

export default App;

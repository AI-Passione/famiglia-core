import { useState, useEffect } from 'react';
import type { AppSettings } from '../types';
import { EngineRoom } from './EngineRoom';
import { Connections } from './Connections';
import { motion, AnimatePresence } from 'framer-motion';

interface SettingsProps {
  settings: AppSettings;
  onSettingsChange: (next: AppSettings) => void;
  githubConnected?: string | null;
  githubError?: string | null;
  onClearOAuthParams?: () => void;
}

const HONORIFIC_OPTIONS = ['Don', 'Donna', 'Boss', 'Capo', 'Consigliere'];

export function Settings({ 
  settings, 
  onSettingsChange,
  githubConnected,
  githubError,
  onClearOAuthParams
}: SettingsProps) {
  const [activeSubTab, setActiveSubTab] = useState('personalization');

  // If we have OAuth params, switch to integration tab
  useEffect(() => {
    if (githubConnected || githubError) {
      setActiveSubTab('integration');
    }
  }, [githubConnected, githubError]);

  const tabs = [
    { id: 'personalization', label: 'Personalization' },
    { id: 'engine_room', label: 'The Engine Room' },
    { id: 'integration', label: 'Integration' }
  ];

  return (
    <div className="space-y-10">
      <header className="space-y-4">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-[#4A0404]/20 rounded-xl border border-[#4A0404]/40">
            <span className="material-symbols-outlined text-[#ffb3b5] text-3xl">settings</span>
          </div>
          <div>
            <h1 className="font-headline text-5xl text-white tracking-tight">Settings</h1>
            <p className="font-body text-[#a38b88] text-sm uppercase tracking-widest mt-1">Command Center Configuration & Telemetry</p>
          </div>
        </div>

        {/* Sub-navigation */}
        <nav className="flex gap-2 p-1 bg-[#131313] border border-[#1c1b1b] rounded-xl w-fit relative">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              className={`relative px-6 py-2 rounded-lg font-label text-[10px] uppercase tracking-widest transition-all z-10 ${
                activeSubTab === tab.id ? 'text-[#ffb3b5]' : 'text-[#a38b88] hover:text-white'
              }`}
            >
              {tab.label}
              {activeSubTab === tab.id && (
                <motion.div
                  layoutId="activeTabIndicator"
                  className="absolute inset-0 bg-[#1c1b1b] rounded-lg border border-[#ffb3b5]/20 shadow-[0_4px_12px_rgba(0,0,0,0.5)] -z-10"
                  transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                />
              )}
            </button>
          ))}
        </nav>
      </header>

      <div className="min-h-[60vh] relative">
        <AnimatePresence mode="wait">
          {activeSubTab === 'personalization' && (
            <motion.div
              key="personalization"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3, ease: "easeOut" }}
              className="space-y-12"
            >
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                {/* Identity Section */}
                <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 space-y-8 shadow-[0_20px_45px_rgba(0,0,0,0.35)]">
                  <div className="flex items-center gap-3 border-b border-white/5 pb-4">
                    <span className="material-symbols-outlined text-[#ffb3b5]">person</span>
                    <h2 className="font-headline text-2xl text-white">Identity & Branding</h2>
                  </div>
                  
                  <div className="space-y-6">
                    <div className="space-y-3">
                      <label htmlFor="famigliaName" className="font-label text-[10px] text-[#ffb3b5] uppercase tracking-[0.2em]">
                        The Famiglia Name
                      </label>
                      <input
                        id="famigliaName"
                        value={settings.famigliaName}
                        onChange={(event) =>
                          onSettingsChange({ ...settings, famigliaName: event.target.value })
                        }
                        placeholder="e.g. La Passione Inc."
                        className="w-full bg-[#171717]/90 border border-[#2e2e2e] rounded-lg px-4 py-3 text-sm font-body text-white placeholder:text-[#666] focus:outline-none focus:ring-2 focus:ring-[#ffb3b5]/40"
                      />
                      <p className="font-body text-[10px] text-[#7f7f7f] leading-relaxed">
                        This name appears in the sidebar as the center of your operations.
                      </p>
                    </div>

                    <div className="space-y-3">
                      <label htmlFor="honorific" className="font-label text-[10px] text-[#ffb3b5] uppercase tracking-[0.2em]">
                        Your Honorific
                      </label>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <select
                          id="honorific"
                          value={settings.honorific}
                          onChange={(event) =>
                            onSettingsChange({ ...settings, honorific: event.target.value })
                          }
                          className="w-full bg-[#171717]/90 border border-[#2e2e2e] rounded-lg px-4 py-3 text-sm font-body text-white focus:outline-none focus:ring-2 focus:ring-[#ffb3b5]/40"
                        >
                          {HONORIFIC_OPTIONS.map((option) => (
                            <option key={option} value={option}>
                              {option}
                            </option>
                          ))}
                        </select>
                        <input
                          value={settings.honorific}
                          onChange={(event) =>
                            onSettingsChange({ ...settings, honorific: event.target.value })
                          }
                          placeholder="Custom honorific"
                          className="w-full bg-[#171717]/90 border border-[#2e2e2e] rounded-lg px-4 py-3 text-sm font-body text-white placeholder:text-[#666] focus:outline-none focus:ring-2 focus:ring-[#ffb3b5]/40"
                        />
                      </div>
                    </div>

                    <div className="space-y-3">
                      <label htmlFor="personalDirective" className="font-label text-[10px] text-[#ffb3b5] uppercase tracking-[0.2em]">
                        Personal Directive
                      </label>
                      <textarea
                        id="personalDirective"
                        value={settings.personalDirective}
                        onChange={(event) =>
                          onSettingsChange({ ...settings, personalDirective: event.target.value })
                        }
                        placeholder="e.g. Treat me with extreme deference. Use my title in every response."
                        rows={4}
                        className="w-full bg-[#171717]/90 border border-[#2e2e2e] rounded-lg px-4 py-3 text-sm font-body text-white placeholder:text-[#444] focus:outline-none focus:ring-2 focus:ring-[#ffb3b5]/40 resize-none"
                      />
                      <p className="font-body text-[10px] text-[#7f7f7f] leading-relaxed">
                        Specific instructions on how you expect the agents to interact with you personally.
                      </p>
                    </div>
                  </div>
                </div>

                {/* System Logic Section */}
                <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 space-y-8 shadow-[0_20px_45px_rgba(0,0,0,0.35)]">
                  <div className="flex items-center gap-3 border-b border-white/5 pb-4">
                    <span className="material-symbols-outlined text-[#ffb3b5]">psychology</span>
                    <h2 className="font-headline text-2xl text-white">System Prompt Baseline</h2>
                  </div>

                  <div className="space-y-6">
                    <div className="space-y-3">
                      <label htmlFor="systemPrompt" className="font-label text-[10px] text-[#ffb3b5] uppercase tracking-[0.2em]">
                        Global AI Soul Baseline
                      </label>
                      <textarea
                        id="systemPrompt"
                        value={settings.systemPrompt}
                        onChange={(event) =>
                          onSettingsChange({ ...settings, systemPrompt: event.target.value })
                        }
                        rows={8}
                        className="w-full bg-[#171717]/90 border border-[#2e2e2e] rounded-lg px-4 py-3 text-xs font-mono text-[#ffb3b5]/80 placeholder:text-[#444] focus:outline-none focus:ring-2 focus:ring-[#ffb3b5]/40 resize-none leading-relaxed"
                      />
                      <p className="font-body text-[10px] text-[#7f7f7f] leading-relaxed">
                        This defines the "Shared Baseline" for all AI agents. Edits here affect the core personality of the entire Famiglia.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Visuals & Notifications */}
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                <div className="xl:col-span-2 bg-[#101010]/80 backdrop-blur-xl border border-[#252525] rounded-2xl p-8 space-y-6">
                  <h2 className="font-headline text-xl text-white">Interface Preferences</h2>
                  <div className="space-y-4">
                    <ToggleRow
                      title="Notifications"
                      description="Enable in-app status pings for important updates."
                      checked={settings.notificationsEnabled}
                      onChange={(checked) =>
                        onSettingsChange({ ...settings, notificationsEnabled: checked })
                      }
                    />
                    <ToggleRow
                      title="Background Animations"
                      description="Render subtle motion in decorative background layers."
                      checked={settings.backgroundAnimationsEnabled}
                      onChange={(checked) =>
                        onSettingsChange({
                          ...settings,
                          backgroundAnimationsEnabled: checked,
                        })
                      }
                    />
                  </div>
                </div>
                
                <div className="flex flex-col justify-center bg-[#4A0404]/5 border border-[#4A0404]/20 rounded-2xl p-8 text-center space-y-2">
                  <p className="font-label text-[10px] uppercase tracking-widest text-[#a38b88]">Active Identity</p>
                  <p data-testid="active-honorific" className="font-headline text-3xl text-white">{settings.honorific}</p>
                  <div className="h-px w-12 bg-[#4A0404]/40 mx-auto my-4" />
                  <p className="font-body text-xs text-[#666] italic">"La Passione is about the art of the agentic AI."</p>
                </div>
              </div>
            </motion.div>
          )}

          {activeSubTab === 'engine_room' && (
            <motion.div 
              key="engine_room"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3, ease: "easeOut" }}
            >
              <EngineRoom />
            </motion.div>
          )}

          {activeSubTab === 'integration' && (
            <motion.div 
              key="integration"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3, ease: "easeOut" }}
            >
              <Connections
                successParam={githubConnected}
                errorParam={githubError}
                onClearParams={onClearOAuthParams}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

interface ToggleRowProps {
  title: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

function ToggleRow({ title, description, checked, onChange }: ToggleRowProps) {
  return (
    <label className="flex items-center justify-between gap-4 border border-[#252525] rounded-lg px-6 py-4 bg-[#141414]/80 cursor-pointer hover:bg-[#181818] transition-all group">
      <div className="space-y-1">
        <p className="font-body text-sm text-white group-hover:text-[#ffb3b5] transition-colors">{title}</p>
        <p className="font-body text-xs text-[#7f7f7f]">{description}</p>
      </div>
      <div className={`relative w-12 h-6 rounded-full transition-all duration-300 ${checked ? 'bg-[#4A0404]' : 'bg-[#222]'}`}>
        <div className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-all duration-300 ${checked ? 'translate-x-6' : 'translate-x-0'}`} />
      </div>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="sr-only"
      />
    </label>
  );
}

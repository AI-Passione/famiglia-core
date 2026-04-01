import type { AppSettings } from '../types';

interface SettingsProps {
  settings: AppSettings;
  onSettingsChange: (next: AppSettings) => void;
}

const HONORIFIC_OPTIONS = ['Don', 'Donna', 'Boss', 'Capo', 'Consigliere'];

export function Settings({ settings, onSettingsChange }: SettingsProps) {
  return (
    <section className="space-y-8">
      <header className="space-y-2">
        <h1 className="font-headline text-5xl text-white tracking-tight">Settings</h1>
        <p className="font-body text-[#a38b88] text-sm max-w-3xl">
          Configure how the Command Center addresses you and tune the visual experience.
          Settings are synced with Command Center API and cached locally in this browser.
        </p>
      </header>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 md:p-8 space-y-6 shadow-[0_20px_45px_rgba(0,0,0,0.35)]">
          <div className="space-y-3">
            <label htmlFor="honorific" className="font-label text-[10px] text-[#ffb3b5] uppercase tracking-[0.2em]">
              Honorific
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
            <p className="font-body text-xs text-[#7f7f7f]">
              Used in greetings across the dashboard, including The Situation Room.
            </p>
          </div>

          <div className="space-y-4">
            <h2 className="font-headline text-xl text-white">Global Options</h2>
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

        <aside className="bg-[#101010]/80 backdrop-blur-xl border border-[#252525] rounded-2xl p-6 space-y-4 shadow-[0_16px_35px_rgba(0,0,0,0.35)]">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-[#a38b88]">
            Preview
          </p>
          <div className="border border-[#282828] bg-[#131313] rounded-xl p-5 space-y-2">
            <p className="font-body text-xs text-[#7f7f7f] uppercase tracking-[0.15em]">
              Situation Room Greeting
            </p>
            <p className="font-headline text-2xl text-white tracking-tight">
              Welcome back, {settings.honorific}
            </p>
          </div>
          <p className="font-body text-xs text-[#666] leading-relaxed">
            Stored in <code>localStorage</code> on this browser only.
          </p>
        </aside>
      </div>
    </section>
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
    <label className="flex items-center justify-between gap-4 border border-[#252525] rounded-lg px-4 py-3 bg-[#141414]/80 cursor-pointer">
      <div className="space-y-1">
        <p className="font-body text-sm text-white">{title}</p>
        <p className="font-body text-xs text-[#7f7f7f]">{description}</p>
      </div>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-5 w-5 accent-[#ffb3b5]"
      />
    </label>
  );
}

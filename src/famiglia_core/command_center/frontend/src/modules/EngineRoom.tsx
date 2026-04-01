import { useEffect, useState } from 'react';
import { API_BASE } from '../config';
import type {
  EngineRoomDockerService,
  EngineRoomMetric,
  EngineRoomObservabilityItem,
  EngineRoomSnapshot,
  EngineRoomTool,
} from '../types';

function formatBytes(value: number | null) {
  if (value == null || Number.isNaN(value)) return 'Unavailable';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(size >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatTimestamp(value: string) {
  return new Date(value).toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function toneClasses(status: string) {
  if (['connected', 'online', 'healthy', 'running', 'ready'].includes(status)) {
    return 'border-[#1f4d35] bg-[#091811] text-[#9ce7bb]';
  }
  if (['reachable'].includes(status)) {
    return 'border-[#5f4a1f] bg-[#181208] text-[#ffd37a]';
  }
  return 'border-[#4A0404] bg-[#190a0a] text-[#ffb3b5]';
}

function SectionHeading({
  eyebrow,
  title,
  blurb,
}: {
  eyebrow: string;
  title: string;
  blurb: string;
}) {
  return (
    <div className="flex items-end justify-between gap-6">
      <div>
        <p className="font-label text-[10px] uppercase tracking-[0.35em] text-[#a38b88]">{eyebrow}</p>
        <h2 className="mt-3 font-headline text-3xl text-on-surface">{title}</h2>
      </div>
      <p className="max-w-2xl text-sm leading-relaxed text-on-surface-variant">{blurb}</p>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="rounded-xl border border-[#201d1d] bg-[#111111]/90 p-5 shadow-[0_24px_80px_rgba(0,0,0,0.25)]">
      <p className="font-label text-[10px] uppercase tracking-[0.25em] text-[#a38b88]">{label}</p>
      <p className="mt-3 font-headline text-3xl text-white">{value}</p>
      <p className="mt-2 text-sm text-on-surface-variant">{hint}</p>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-[10px] font-label uppercase tracking-[0.25em] ${toneClasses(status)}`}
    >
      {status.replaceAll('_', ' ')}
    </span>
  );
}

function ToolCard({ tool }: { tool: EngineRoomTool }) {
  return (
    <article className="rounded-xl border border-[#211a1a] bg-[#0f0f0f]/95 p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-label text-[10px] uppercase tracking-[0.3em] text-[#a38b88]">{tool.category}</p>
          <h3 className="mt-2 font-headline text-xl text-white">{tool.name}</h3>
        </div>
        <StatusPill status={tool.status} />
      </div>
      <p className="mt-4 text-sm leading-relaxed text-on-surface-variant">{tool.description}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <span className={`rounded-full px-3 py-1 text-[10px] font-label uppercase tracking-[0.2em] ${tool.configured ? 'bg-[#151f18] text-[#9ce7bb]' : 'bg-[#1a1212] text-[#ffb3b5]'}`}>
          {tool.configured ? 'Configured' : 'Needs config'}
        </span>
        <span className={`rounded-full px-3 py-1 text-[10px] font-label uppercase tracking-[0.2em] ${tool.connected ? 'bg-[#151f18] text-[#9ce7bb]' : 'bg-[#181818] text-[#8b8b8b]'}`}>
          {tool.connected ? 'Connected' : 'Not connected'}
        </span>
      </div>
      <p className="mt-4 border-t border-[#1f1b1b] pt-4 text-xs text-[#b6a7a4]">{tool.detail}</p>
    </article>
  );
}

function DockerServiceCard({ service }: { service: EngineRoomDockerService }) {
  const primaryStatus = service.health !== 'unknown' ? service.health : service.state;
  return (
    <article className="rounded-xl border border-[#211a1a] bg-[#0f0f0f]/95 p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-headline text-xl text-white">{service.name}</h3>
          <p className="mt-1 text-xs uppercase tracking-[0.2em] text-[#8b817f]">
            {service.profiles.length ? service.profiles.join(', ') : 'core runtime'}
          </p>
        </div>
        <StatusPill status={primaryStatus} />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm text-on-surface-variant">
        <div>
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-[#a38b88]">State</p>
          <p className="mt-1">{service.state.replaceAll('_', ' ')}</p>
        </div>
        <div>
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-[#a38b88]">Reachability</p>
          <p className="mt-1">{service.reachable ? 'Port reachable' : 'No port response'}</p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {service.ports.length ? (
          service.ports.map(port => (
            <span key={`${service.name}-${port.raw}`} className="rounded-full bg-[#171717] px-3 py-1 text-[10px] font-label uppercase tracking-[0.2em] text-[#d0c4c2]">
              {port.host_port}:{port.container_port}
            </span>
          ))
        ) : (
          <span className="rounded-full bg-[#171717] px-3 py-1 text-[10px] font-label uppercase tracking-[0.2em] text-[#7f7a79]">
            No host port
          </span>
        )}
      </div>
    </article>
  );
}

function ObservabilityCard({ item }: { item: EngineRoomObservabilityItem }) {
  const state = item.reachable ? 'online' : item.configured ? 'standby' : 'offline';
  return (
    <article className="rounded-xl border border-[#211a1a] bg-[#0f0f0f]/95 p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-headline text-xl text-white">{item.name}</h3>
          <p className="mt-2 text-sm text-on-surface-variant">{item.description}</p>
        </div>
        <StatusPill status={state} />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm text-on-surface-variant">
        <div>
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-[#a38b88]">Service</p>
          <p className="mt-1">{item.service_name}</p>
        </div>
        <div>
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-[#a38b88]">Endpoint</p>
          <p className="mt-1">{item.url}</p>
        </div>
      </div>
    </article>
  );
}

function MetricStrip({ metric }: { metric: EngineRoomMetric }) {
  const accent =
    metric.tone === 'good'
      ? 'text-[#9ce7bb] border-[#1f4d35]'
      : metric.tone === 'warn'
        ? 'text-[#ffd37a] border-[#5f4a1f]'
        : 'text-[#d0c4c2] border-[#282222]';

  return (
    <div className={`rounded-xl border bg-[#0f0f0f]/95 p-5 ${accent}`}>
      <p className="font-label text-[10px] uppercase tracking-[0.25em] text-[#a38b88]">{metric.label}</p>
      <p className="mt-3 font-headline text-2xl">{metric.value}</p>
      <p className="mt-2 text-sm text-on-surface-variant">{metric.hint}</p>
    </div>
  );
}

export function EngineRoom() {
  const [snapshot, setSnapshot] = useState<EngineRoomSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const load = async () => {
      try {
        const response = await fetch(`${API_BASE}/engine-room`);
        if (!response.ok) {
          throw new Error('Engine Room telemetry request failed.');
        }
        const payload = (await response.json()) as EngineRoomSnapshot;
        if (isMounted) {
          setSnapshot(payload);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Unable to reach the Engine Room endpoint.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    load();
    const interval = window.setInterval(load, 15000);
    return () => {
      isMounted = false;
      window.clearInterval(interval);
    };
  }, []);

  if (loading && !snapshot) {
    return (
      <section
        data-testid="engine-room-page"
        className="rounded-[28px] border border-[#231f1f] bg-[radial-gradient(circle_at_top,_rgba(74,4,4,0.28),_transparent_48%),linear-gradient(180deg,#0e0e0e_0%,#080808_100%)] p-10"
      >
        <p className="font-label text-[10px] uppercase tracking-[0.35em] text-[#a38b88]">Engine Room</p>
        <div className="mt-6 flex items-center gap-4 text-[#ffb3b5]">
          <span className="material-symbols-outlined animate-pulse">precision_manufacturing</span>
          <p className="text-sm text-on-surface-variant">Polling local telemetry, Docker reachability, and tool readiness.</p>
        </div>
      </section>
    );
  }

  if (error && !snapshot) {
    return (
      <section
        data-testid="engine-room-page"
        className="rounded-[28px] border border-[#4A0404] bg-[#120909] p-10"
      >
        <p className="font-label text-[10px] uppercase tracking-[0.35em] text-[#ffb3b5]">Engine Room</p>
        <h2 className="mt-4 font-headline text-3xl text-white">Local telemetry is currently unreachable</h2>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-on-surface-variant">{error}</p>
      </section>
    );
  }

  if (!snapshot) return null;

  const cpuValue =
    snapshot.host.cpu.estimated_load_percent != null
      ? `${snapshot.host.cpu.estimated_load_percent.toFixed(1)}%`
      : 'Unavailable';
  const memoryValue =
    snapshot.host.memory.usage_percent != null
      ? `${snapshot.host.memory.usage_percent.toFixed(1)}%`
      : 'Unavailable';
  const observabilityHint = `${snapshot.observability.summary.reachable}/${snapshot.observability.summary.total} stacks reachable`;

  return (
    <section
      data-testid="engine-room-page"
      className="space-y-8 rounded-[28px] border border-[#231f1f] bg-[radial-gradient(circle_at_top,_rgba(74,4,4,0.22),_transparent_48%),linear-gradient(180deg,#0f0f10_0%,#080808_100%)] p-8 md:p-10 shadow-[0_40px_140px_rgba(0,0,0,0.35)]"
    >
      <SectionHeading
        eyebrow="Local Control Surface"
        title="The Engine Room"
        blurb="Full local-only inventory of tools, Docker health, host pressure, and the observability spine that supports the famiglia runtime."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <SummaryCard
          label="Tool Readiness"
          value={`${snapshot.tools.summary.ready}/${snapshot.tools.summary.total}`}
          hint={`${snapshot.tools.summary.connected} active connections across local tools.`}
        />
        <SummaryCard
          label="Docker Health"
          value={`${snapshot.docker.summary.healthy}/${snapshot.docker.summary.declared}`}
          hint={`${snapshot.docker.summary.reachable} services respond on local ports.`}
        />
        <SummaryCard
          label="CPU Load"
          value={cpuValue}
          hint={`${snapshot.host.cpu.cores} cores | load avg ${snapshot.host.cpu.load_average?.join(' / ') || 'n/a'}`}
        />
        <SummaryCard
          label="Observability"
          value={`${snapshot.observability.summary.configured}/${snapshot.observability.summary.total}`}
          hint={observabilityHint}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        <div className="xl:col-span-4 space-y-6">
          <div className="rounded-2xl border border-[#211a1a] bg-[#0f0f0f]/95 p-6">
            <p className="font-label text-[10px] uppercase tracking-[0.3em] text-[#a38b88]">Host Snapshot</p>
            <div className="mt-5 space-y-4 text-sm text-on-surface-variant">
              <div>
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-[#a38b88]">Platform</p>
                <p className="mt-1 text-white">
                  {snapshot.host.platform.system} {snapshot.host.platform.release} on {snapshot.host.platform.machine}
                </p>
              </div>
              <div>
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-[#a38b88]">Uptime</p>
                <p className="mt-1">{snapshot.host.uptime.display}</p>
              </div>
              <div>
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-[#a38b88]">Memory</p>
                <p className="mt-1 text-white">
                  {formatBytes(snapshot.host.memory.used_bytes)} used of {formatBytes(snapshot.host.memory.total_bytes)}
                </p>
              </div>
              <div>
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-[#a38b88]">Disk</p>
                <p className="mt-1 text-white">
                  {formatBytes(snapshot.host.disk.used_bytes)} used of {formatBytes(snapshot.host.disk.total_bytes)}
                </p>
              </div>
              <div>
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-[#a38b88]">Refreshed</p>
                <p className="mt-1">{formatTimestamp(snapshot.generated_at)}</p>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            {snapshot.observability.metrics.map(metric => (
              <MetricStrip key={metric.label} metric={metric} />
            ))}
          </div>
        </div>

        <div className="xl:col-span-8 space-y-6">
          <div>
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <p className="font-label text-[10px] uppercase tracking-[0.3em] text-[#a38b88]">Tool Inventory</p>
                <h3 className="mt-2 font-headline text-2xl text-white">Live capability roster</h3>
              </div>
              <p className="text-sm text-on-surface-variant">Includes GitHub, Notion, Slack, web search, model runtime, traces, and local warehouse surfaces.</p>
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {snapshot.tools.items.map(tool => (
                <ToolCard key={tool.slug} tool={tool} />
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        <div className="xl:col-span-7">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <p className="font-label text-[10px] uppercase tracking-[0.3em] text-[#a38b88]">Docker Surface</p>
              <h3 className="mt-2 font-headline text-2xl text-white">Container and port health</h3>
            </div>
            <StatusPill status={snapshot.docker.available ? 'ready' : 'inactive'} />
          </div>

          {snapshot.docker.diagnostics.length > 0 && (
            <div className="mb-4 rounded-xl border border-[#4A0404] bg-[#140b0b] p-4 text-sm text-[#d8c0bc]">
              {snapshot.docker.diagnostics[0]}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {snapshot.docker.services.map(service => (
              <DockerServiceCard key={service.name} service={service} />
            ))}
          </div>
        </div>

        <div className="xl:col-span-5">
          <div className="mb-4">
            <p className="font-label text-[10px] uppercase tracking-[0.3em] text-[#a38b88]">Observability Spine</p>
            <h3 className="mt-2 font-headline text-2xl text-white">Dashboards, logs, metrics, traces</h3>
          </div>
          <div className="space-y-4">
            {snapshot.observability.items.map(item => (
              <ObservabilityCard key={item.service_name} item={item} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

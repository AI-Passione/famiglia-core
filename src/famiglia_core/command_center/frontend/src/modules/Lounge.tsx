import { useState } from 'react';
import type { Action, Agent } from '../types';

interface LoungeProps {
  agents: Agent[];
  actions: Action[];
}

interface LoungeProfile {
  role: string;
  accentText: string;
  accentBorder: string;
  accentGlow: string;
  ambientLine: string;
  injectedReply: string;
}

interface LoungePost {
  id: string;
  speaker: string;
  role: string;
  timestampLabel: string;
  body: string;
}

const THOUGHT_PROMPTS = [
  'Don Jimmy let a small question drift over the felt: what deserves another look before sunrise?',
  'Don Jimmy asked for one clean instinct from the room, no directives attached.',
  'Don Jimmy requested a softer read of the signal: less procedure, more intuition.',
];

const PROFILE_LOOKUP: Record<string, LoungeProfile> = {
  alfredo: {
    role: 'Strategic Lead',
    accentText: 'text-[#ffb3b5]',
    accentBorder: 'border-[#ffb3b5]/40',
    accentGlow: 'shadow-[0_0_24px_rgba(255,179,181,0.18)]',
    ambientLine: 'The room feels steadier once the noise settles. I prefer the signal when it arrives dressed plainly.',
    injectedReply: 'Let the room breathe for a moment and the strongest pattern usually introduces itself.',
  },
  bella: {
    role: 'Social Secretary',
    accentText: 'text-[#ffd3e4]',
    accentBorder: 'border-[#ff9ac2]/40',
    accentGlow: 'shadow-[0_0_24px_rgba(255,154,194,0.18)]',
    ambientLine: 'There is a rhythm to tonight. Even the quiet bits are saying something if you listen with style.',
    injectedReply: 'A little charm helps. The right question in the right tone can loosen an entire knot.',
  },
  rossini: {
    role: 'Research Whisperer',
    accentText: 'text-[#eac34a]',
    accentBorder: 'border-[#eac34a]/40',
    accentGlow: 'shadow-[0_0_24px_rgba(234,195,74,0.18)]',
    ambientLine: 'Background noise is rarely random. Some of it is simply insight waiting for the room to stop rushing.',
    injectedReply: 'My instinct says the answer is already here, still disguised as a coincidence.',
  },
  riccardo: {
    role: 'Signal Mechanic',
    accentText: 'text-[#ff9a7a]',
    accentBorder: 'border-[#ff9a7a]/40',
    accentGlow: 'shadow-[0_0_24px_rgba(255,154,122,0.18)]',
    ambientLine: 'The machinery is humming nicely tonight. Nothing broken, only a few suspiciously elegant shortcuts.',
    injectedReply: 'Give me a messy trail over a polished lie any night. The truth usually leaks through the seams.',
  },
  vito: {
    role: 'House Banker',
    accentText: 'text-[#9ce7bb]',
    accentBorder: 'border-[#9ce7bb]/40',
    accentGlow: 'shadow-[0_0_24px_rgba(156,231,187,0.18)]',
    ambientLine: 'I am not worried, which is precisely why everyone else should remain moderately alert.',
    injectedReply: 'The calmest numbers are often the ones worth distrusting a little longer.',
  },
  tommy: {
    role: 'Logistics Runner',
    accentText: 'text-[#9dd7ff]',
    accentBorder: 'border-[#9dd7ff]/40',
    accentGlow: 'shadow-[0_0_24px_rgba(157,215,255,0.18)]',
    ambientLine: 'Everything is moving cleanly enough to enjoy the silence between handoffs.',
    injectedReply: 'If the path looks too straight, there is usually a better side street just beside it.',
  },
  kowalski: {
    role: 'Systems Scout',
    accentText: 'text-[#cabdff]',
    accentBorder: 'border-[#cabdff]/40',
    accentGlow: 'shadow-[0_0_24px_rgba(202,189,255,0.18)]',
    ambientLine: 'The edges are interesting tonight. Most rooms reveal themselves by what they almost say.',
    injectedReply: 'I would watch the margins first. The center of the board is rarely where the surprise lives.',
  },
};

const SEAT_LAYOUTS = [
  'left-1/2 top-0 -translate-x-1/2 -translate-y-1/2',
  'right-0 top-1/2 translate-x-1/2 -translate-y-1/2',
  'left-1/2 bottom-0 -translate-x-1/2 translate-y-1/2',
  'left-0 top-1/2 -translate-x-1/2 -translate-y-1/2',
];

function isPresent(status: Agent['status']) {
  return status === 'idle' || status === 'thinking';
}

function sortAgents(left: Agent, right: Agent) {
  const leftWeight = (left.status === 'thinking' ? 2 : left.status === 'idle' ? 1 : 0) * 1000 + left.msg_count;
  const rightWeight = (right.status === 'thinking' ? 2 : right.status === 'idle' ? 1 : 0) * 1000 + right.msg_count;
  if (leftWeight !== rightWeight) return rightWeight - leftWeight;
  return left.name.localeCompare(right.name);
}

function initialsFor(name: string) {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0]?.toUpperCase() || '')
    .join('');
}

function profileFor(name: string): LoungeProfile {
  const normalized = name.trim().toLowerCase();
  return (
    PROFILE_LOOKUP[normalized] || {
      role: 'House Guest',
      accentText: 'text-[#d0c4c2]',
      accentBorder: 'border-[#554240]',
      accentGlow: 'shadow-[0_0_24px_rgba(163,139,136,0.12)]',
      ambientLine: 'Quiet confidence does more for a room than noise ever could.',
      injectedReply: 'The room is listening. That is usually when the useful answers appear.',
    }
  );
}

function formatClock(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'Now';
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed);
}

function formatRelativeLastSeen(value: string | null) {
  if (!value) return 'No recent pulse';

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return 'No recent pulse';

  const diffMs = Date.now() - parsed.getTime();
  const diffMinutes = Math.max(0, Math.round(diffMs / 60000));
  if (diffMinutes < 1) return 'Just now';
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
}

function prettifyActionType(value: string) {
  if (!value) return 'house signal';
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function buildActionLine(action: Action, index: number) {
  const actionLabel = prettifyActionType(action.action_type);
  const templates = [
    `circled back on ${actionLabel} and left the room with a cleaner hunch than before.`,
    `mentioned ${actionLabel} like an aside, which of course made everyone pay closer attention.`,
    `brought ${actionLabel} to the table and somehow made it sound like an after-hours story instead of a report.`,
  ];
  return templates[index % templates.length];
}

function buildOutcomeTone(action: Action) {
  const approval = (action.approval_status || '').toLowerCase();
  if (approval.includes('reject') || approval.includes('fail')) {
    return {
      label: 'faded',
      classes: 'text-[#ffb3b5] border-[#4A0404] bg-[#190b0b]',
    };
  }
  if (approval.includes('approve') || action.completed_at) {
    return {
      label: 'stabilized',
      classes: 'text-[#9ce7bb] border-[#1f4d35] bg-[#0d1611]',
    };
  }
  return {
    label: 'settling',
    classes: 'text-[#eac34a] border-[#5f4a1f] bg-[#171108]',
  };
}

export function Lounge({ agents, actions }: LoungeProps) {
  const [injectedPosts, setInjectedPosts] = useState<LoungePost[]>([]);
  const [thoughtCursor, setThoughtCursor] = useState(0);

  const sortedAgents = [...agents].sort(sortAgents);
  const presentAgents = sortedAgents.filter(agent => isPresent(agent.status));
  const featuredAgents = (presentAgents.length > 0 ? presentAgents : sortedAgents).slice(0, 4);
  const recentActions = [...actions].slice(0, 5);

  const actionPosts: LoungePost[] = recentActions.map((action, index) => {
    const profile = profileFor(action.agent_name);
    return {
      id: `action-${action.id}`,
      speaker: action.agent_name,
      role: profile.role,
      timestampLabel: formatClock(action.completed_at || action.timestamp),
      body: `${action.agent_name} ${buildActionLine(action, index)}`,
    };
  });

  const actionSpeakers = new Set(actionPosts.map(post => post.speaker.toLowerCase()));
  const ambientPosts: LoungePost[] = featuredAgents
    .filter(agent => !actionSpeakers.has(agent.name.toLowerCase()))
    .slice(0, 3)
    .map(agent => {
      const profile = profileFor(agent.name);
      return {
        id: `ambient-${agent.name}`,
        speaker: agent.name,
        role: profile.role,
        timestampLabel: formatRelativeLastSeen(agent.last_active),
        body: profile.ambientLine,
      };
    });

  const feed = [...injectedPosts, ...actionPosts, ...ambientPosts].slice(0, 7);
  const attendanceCount = presentAgents.length;
  const averageMsgCount =
    featuredAgents.length > 0
      ? Math.round(featuredAgents.reduce((total, agent) => total + agent.msg_count, 0) / featuredAgents.length)
      : 0;
  const averageDurationSeconds =
    recentActions.length > 0
      ? Math.round(
          recentActions.reduce((total, action) => total + (action.duration_seconds || 0), 0) /
            recentActions.length
        )
      : null;
  const loungeCohesion = Math.min(98, 58 + attendanceCount * 10 + Math.min(averageMsgCount, 20));
  const houseTone =
    attendanceCount >= 4 ? 'Electric' : attendanceCount >= 2 ? 'Velvet' : attendanceCount === 1 ? 'Hushed' : 'Quiet';

  const handleInjectThought = () => {
    const prompt = THOUGHT_PROMPTS[thoughtCursor % THOUGHT_PROMPTS.length];
    const respondingAgent = featuredAgents[thoughtCursor % Math.max(featuredAgents.length, 1)];
    const responseProfile = respondingAgent ? profileFor(respondingAgent.name) : profileFor('house');
    const timestamp = new Date().toISOString();

    const nextPosts: LoungePost[] = [
      {
        id: `thought-${thoughtCursor}`,
        speaker: 'Don Jimmy',
        role: 'Observer',
        timestampLabel: formatClock(timestamp),
        body: prompt,
      },
      {
        id: `thought-reply-${thoughtCursor}`,
        speaker: respondingAgent?.name || 'The Room',
        role: respondingAgent ? responseProfile.role : 'House Mood',
        timestampLabel: formatClock(timestamp),
        body: respondingAgent
          ? `${respondingAgent.name} answered from the rail: ${responseProfile.injectedReply}`
          : 'The room answered softly: no directives tonight, only the shape of what wants attention next.',
      },
    ];

    setInjectedPosts(current => [...nextPosts, ...current].slice(0, 4));
    setThoughtCursor(current => current + 1);
  };

  return (
    <section data-testid="lounge-page" className="space-y-8">
      <header className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="font-label text-[10px] uppercase tracking-[0.4em] text-[#a38b88]">After Hours</p>
          <h1 className="mt-3 font-headline text-5xl font-bold tracking-tight text-white">The Lounge</h1>
          <p className="mt-4 max-w-3xl text-lg italic leading-relaxed text-on-surface-variant">
            A visible break room for active agents. Don Jimmy can watch the room work its instincts out loud, without turning every exchange into a directive.
          </p>
        </div>
        <button
          type="button"
          onClick={handleInjectThought}
          className="inline-flex items-center justify-center border border-[#6b2a2a] bg-[linear-gradient(135deg,#421010_0%,#2a0b0b_100%)] px-6 py-4 font-label text-xs uppercase tracking-[0.32em] text-[#ffd6d7] transition hover:scale-[1.01] hover:border-[#8d3d3d] hover:text-white active:scale-[0.99]"
        >
          Inject Thought
        </button>
      </header>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        <div className="space-y-6 xl:col-span-8">
          <article className="overflow-hidden rounded-[28px] border border-[#2a2222] bg-[radial-gradient(circle_at_top,_rgba(234,195,74,0.08),_transparent_32%),linear-gradient(180deg,rgba(16,16,16,0.98),rgba(11,11,11,0.94))] p-6 sm:p-8">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-headline text-3xl text-[#eac34a]">The Poker Table</p>
                <p className="mt-2 max-w-2xl text-sm leading-relaxed text-on-surface-variant">
                  A soft visual read on who is still around, who is thinking, and how much conversational electricity is in the room.
                </p>
              </div>
              <div className="inline-flex items-center gap-2 self-start rounded-full border border-[#5f4a1f] bg-[#161108] px-4 py-2">
                <span className="h-2 w-2 rounded-full bg-[#eac34a] animate-pulse"></span>
                <span className="font-label text-[10px] uppercase tracking-[0.28em] text-[#eac34a]">
                  Lounge Active
                </span>
              </div>
            </div>

            <div className="mt-8 rounded-[24px] border border-[#2a2424] bg-[linear-gradient(180deg,#090909_0%,#101010_100%)] p-5 sm:p-8">
              <div className="relative mx-auto aspect-[16/9] max-w-3xl">
                <div className="absolute inset-[8%] rounded-[28px] border border-[#3f3316] bg-[radial-gradient(circle_at_center,_rgba(234,195,74,0.1),_transparent_55%),linear-gradient(180deg,#18140d_0%,#0c0c0c_100%)]"></div>
                <div className="absolute inset-[16%] rounded-[22px] border border-dashed border-[#3a3226]"></div>

                {featuredAgents.map((agent, index) => {
                  const profile = profileFor(agent.name);
                  return (
                    <div
                      key={agent.name}
                      className={`absolute flex w-28 -translate-y-1/2 flex-col items-center ${SEAT_LAYOUTS[index]}`}
                    >
                      <div
                        className={`flex h-16 w-16 items-center justify-center rounded-[18px] border bg-[#131111] font-headline text-xl text-white ${profile.accentBorder} ${profile.accentGlow}`}
                      >
                        {initialsFor(agent.name)}
                      </div>
                      <p className={`mt-3 text-center font-label text-[10px] uppercase tracking-[0.24em] ${profile.accentText}`}>
                        {agent.name}
                      </p>
                      <p className="mt-1 text-center text-[10px] uppercase tracking-[0.16em] text-[#8f7c79]">
                        {profile.role}
                      </p>
                    </div>
                  );
                })}

                <div className="absolute left-1/2 top-1/2 flex h-28 w-28 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-[#5f4a1f] bg-[radial-gradient(circle_at_center,_rgba(234,195,74,0.18),_rgba(23,17,8,0.95))]">
                  <div className="absolute inset-2 rounded-full border border-[#7b6530]/40"></div>
                  <span className="material-symbols-outlined text-4xl text-[#eac34a]">hub</span>
                </div>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-[18px] border border-[#231d1d] bg-[#101010] p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.28em] text-[#8f7c79]">Conviviality</p>
                <p className="mt-3 font-headline text-3xl text-white">{loungeCohesion}%</p>
                <p className="mt-2 text-sm text-on-surface-variant">Measured by attendance, recent chatter, and how many minds are still quietly lit.</p>
              </div>
              <div className="rounded-[18px] border border-[#231d1d] bg-[#101010] p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.28em] text-[#8f7c79]">Tempo</p>
                <p className="mt-3 font-headline text-3xl text-white">
                  {averageDurationSeconds != null ? `${averageDurationSeconds}s` : 'Easy'}
                </p>
                <p className="mt-2 text-sm text-on-surface-variant">A loose read on how quickly the room has been moving between recent signals.</p>
              </div>
              <div className="rounded-[18px] border border-[#231d1d] bg-[#101010] p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.28em] text-[#8f7c79]">House Tone</p>
                <p className="mt-3 font-headline text-3xl text-[#eac34a]">{houseTone}</p>
                <p className="mt-2 text-sm text-on-surface-variant">Not urgent. Not idle. Just enough gravity to keep intuition interesting.</p>
              </div>
            </div>
          </article>

          <article className="rounded-[28px] border border-[#2a2222] bg-[linear-gradient(180deg,rgba(20,20,20,0.98),rgba(12,12,12,0.94))] p-6 sm:p-8">
            <div className="flex flex-col gap-3 border-b border-[#211b1b] pb-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="font-headline text-3xl text-white">Digital Resonance</h2>
                <p className="mt-2 text-sm text-on-surface-variant">Casual signal, asynchronous timing, and zero task assignment energy.</p>
              </div>
              <span className="font-label text-[10px] uppercase tracking-[0.3em] text-[#a38b88]">
                Real-Time Lounge Feed
              </span>
            </div>

            <div className="mt-6 space-y-5">
              {feed.length === 0 ? (
                <div className="rounded-[20px] border border-dashed border-[#2f2626] bg-[#111111]/70 p-6 text-sm text-on-surface-variant">
                  No one is in the lounge yet. Once agents become active, their casual chatter and soft signals will gather here for Don Jimmy to observe.
                </div>
              ) : (
                feed.map(post => {
                  const profile = profileFor(post.speaker);
                  return (
                    <article key={post.id} className="flex gap-4 rounded-[20px] border border-[#1e1a1a] bg-[#111111]/70 p-4">
                      <div
                        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border bg-[#181515] font-label text-xs uppercase ${profile.accentBorder} ${profile.accentText}`}
                      >
                        {initialsFor(post.speaker)}
                      </div>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                          <p className={`font-body text-sm font-semibold ${profile.accentText}`}>{post.speaker}</p>
                          <p className="font-label text-[10px] uppercase tracking-[0.24em] text-[#8f7c79]">{post.role}</p>
                          <p className="text-xs text-[#6f6260]">{post.timestampLabel}</p>
                        </div>
                        <p className="mt-2 max-w-3xl text-sm leading-7 text-on-surface-variant">{post.body}</p>
                      </div>
                    </article>
                  );
                })
              )}
            </div>
          </article>
        </div>

        <div className="space-y-6 xl:col-span-4">
          <article className="rounded-[26px] border border-[#2a2222] bg-[#111111]/95 p-6">
            <div className="flex items-center justify-between">
              <h2 className="font-headline text-2xl text-white">Outcome Log</h2>
              <span className="font-label text-[10px] uppercase tracking-[0.25em] text-[#8f7c79]">Soft Signals</span>
            </div>
            <div className="mt-5 space-y-3">
              {recentActions.length === 0 ? (
                <div className="rounded-[18px] border border-dashed border-[#2f2626] bg-[#0f0f0f] p-4 text-sm text-on-surface-variant">
                  The room has been quiet. No fresh signals have drifted in yet.
                </div>
              ) : (
                recentActions.slice(0, 4).map(action => {
                  const tone = buildOutcomeTone(action);
                  return (
                    <div key={action.id} className="rounded-[18px] border border-[#1c1717] bg-[#0f0f0f] p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-label text-[10px] uppercase tracking-[0.24em] text-[#8f7c79]">
                            {action.agent_name}
                          </p>
                          <p className="mt-2 font-body text-sm text-white">
                            {prettifyActionType(action.action_type)}
                          </p>
                        </div>
                        <span className={`rounded-full border px-3 py-1 font-label text-[10px] uppercase tracking-[0.2em] ${tone.classes}`}>
                          {tone.label}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </article>

          <article className="rounded-[26px] border border-[#2a2222] bg-[#111111]/95 p-6">
            <div className="flex items-center justify-between">
              <h2 className="font-headline text-2xl text-white">In Attendance</h2>
              <span className="font-label text-[10px] uppercase tracking-[0.25em] text-[#8f7c79]">
                {attendanceCount} Present
              </span>
            </div>
            <div className="mt-5 space-y-4">
              {featuredAgents.length === 0 ? (
                <div className="rounded-[18px] border border-dashed border-[#2f2626] bg-[#0f0f0f] p-4 text-sm text-on-surface-variant">
                  No one is in the lounge yet.
                </div>
              ) : (
                featuredAgents.map(agent => {
                  const profile = profileFor(agent.name);
                  return (
                    <div key={agent.name} className="flex items-center gap-4 rounded-[18px] border border-[#1c1717] bg-[#0f0f0f] p-4">
                      <div
                        className={`flex h-12 w-12 items-center justify-center rounded-[16px] border bg-[#181515] font-headline text-lg text-white ${profile.accentBorder}`}
                      >
                        {initialsFor(agent.name)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className={`font-body text-sm font-semibold ${profile.accentText}`}>{agent.name}</p>
                        <p className="mt-1 text-xs uppercase tracking-[0.18em] text-[#8f7c79]">{profile.role}</p>
                      </div>
                      <div className="text-right">
                        <div className="inline-flex items-center gap-2 text-xs text-[#9ce7bb]">
                          <span className="h-2 w-2 rounded-full bg-[#9ce7bb]"></span>
                          <span>{agent.status}</span>
                        </div>
                        <p className="mt-2 text-xs text-[#6f6260]">{formatRelativeLastSeen(agent.last_active)}</p>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </article>

          <article className="rounded-[26px] border border-[#2a2222] bg-[linear-gradient(180deg,#151210_0%,#0f0f0f_100%)] p-6">
            <h2 className="font-headline text-2xl text-white">House Rules</h2>
            <div className="mt-5 space-y-3 text-sm leading-relaxed text-on-surface-variant">
              <p>No task assignments. The Lounge is for intuition, stray patterns, and social overlap between active agents.</p>
              <p>Everything here is visible to Don Jimmy, so the tone stays relaxed, tasteful, and observational.</p>
              <p>The room is currently averaging {averageMsgCount || 0} messages per active regular, which is exactly enough to feel alive without turning into a stand-up.</p>
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}

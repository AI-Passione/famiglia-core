import { useState } from 'react';
import type { FamigliaAgent, ActionLog, RecurringTask, ScheduleConfig, Task } from '../types';

type AgendaView = 'schedule' | 'week' | 'month';
type AgendaEntryKind = 'task' | 'recurring';

interface AgendaProps {
  agents: FamigliaAgent[];
  actions: ActionLog[];
  tasks: Task[];
  recurringTasks: RecurringTask[];
  honorific: string;
  fullName: string;
}

interface AgendaEntry {
  id: string;
  sourceId: number;
  title: string;
  details: string;
  start: Date;
  end: Date;
  kind: AgendaEntryKind;
  priority: string;
  status: string;
  agent: string | null;
}

const VIEW_OPTIONS: Array<{ id: AgendaView; label: string }> = [
  { id: 'schedule', label: 'Schedule' },
  { id: 'week', label: 'Weekly' },
  { id: 'month', label: 'Monthly' },
];

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const WEEK_HOUR_START = 6;
const WEEK_HOUR_END = 22;
const WEEK_HOUR_HEIGHT = 52;
const DEFAULT_EVENT_MINUTES = 90;
const SCHEDULE_WINDOW_DAYS = 14;

const priorityStyles: Record<string, { chip: string; border: string; dot: string }> = {
  critical: {
    chip: 'bg-[#4b1318] text-[#ffd4d8] border border-[#7f2932]',
    border: 'border-l-[#ff7f88]',
    dot: 'bg-[#ff7f88]',
  },
  high: {
    chip: 'bg-[#3f1e0d] text-[#ffd9b9] border border-[#86512c]',
    border: 'border-l-[#ffb46b]',
    dot: 'bg-[#ffb46b]',
  },
  medium: {
    chip: 'bg-[#122938] text-[#c7ebff] border border-[#295773]',
    border: 'border-l-[#6bc7ff]',
    dot: 'bg-[#6bc7ff]',
  },
  low: {
    chip: 'bg-[#1a2d20] text-[#d7f8dd] border border-[#32543d]',
    border: 'border-l-[#87d89b]',
    dot: 'bg-[#87d89b]',
  },
};

const statusStyles: Record<string, string> = {
  queued: 'bg-[#15202c] text-[#99d3ff]',
  in_progress: 'bg-[#2e2414] text-[#ffd79c]',
  drafted: 'bg-[#221a30] text-[#d3b4ff]',
  completed: 'bg-[#17271d] text-[#a8efbc]',
  failed: 'bg-[#321619] text-[#ffb1b7]',
  cancelled: 'bg-[#222326] text-[#c7cbd1]',
  recurring: 'bg-[#1f2430] text-[#cdd6f4]',
};

function parseMaybeDate(value?: string | null): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0, 0);
}

function endOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59, 999);
}

function addDays(date: Date, amount: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + amount);
  return result;
}

function addMinutes(date: Date, amount: number): Date {
  return new Date(date.getTime() + amount * 60 * 1000);
}

function addMonths(date: Date, amount: number): Date {
  return new Date(date.getFullYear(), date.getMonth() + amount, 1, date.getHours(), date.getMinutes(), 0, 0);
}

function startOfWeek(date: Date): Date {
  const result = startOfDay(date);
  const mondayOffset = (result.getDay() + 6) % 7;
  result.setDate(result.getDate() - mondayOffset);
  return result;
}

function endOfWeek(date: Date): Date {
  return endOfDay(addDays(startOfWeek(date), 6));
}

function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1, 0, 0, 0, 0);
}

function endOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0, 23, 59, 59, 999);
}

function isSameDay(left: Date, right: Date): boolean {
  return (
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  );
}

function isSameMonth(left: Date, right: Date): boolean {
  return left.getFullYear() === right.getFullYear() && left.getMonth() === right.getMonth();
}

function isToday(date: Date): boolean {
  return isSameDay(date, new Date());
}

function formatDayKey(date: Date): string {
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

function toPythonWeekday(date: Date): number {
  return (date.getDay() + 6) % 7;
}

function normalizePriority(priority?: string | null): string {
  const normalized = (priority || 'medium').toLowerCase();
  return priorityStyles[normalized] ? normalized : 'medium';
}

function normalizeStatus(status?: string | null): string {
  const normalized = (status || 'queued').toLowerCase();
  return statusStyles[normalized] ? normalized : 'queued';
}

function getTaskStart(task: Task): Date | null {
  return parseMaybeDate(task.eta_pickup_at) || parseMaybeDate(task.created_at);
}

function getTaskEnd(task: Task, start: Date): Date {
  return (
    parseMaybeDate(task.completed_at) ||
    parseMaybeDate(task.eta_completion_at) ||
    addMinutes(start, DEFAULT_EVENT_MINUTES)
  );
}

function sortEntries(entries: AgendaEntry[]): AgendaEntry[] {
  return [...entries].sort((left, right) => {
    if (left.start.getTime() !== right.start.getTime()) {
      return left.start.getTime() - right.start.getTime();
    }
    return left.title.localeCompare(right.title);
  });
}

function buildTaskEntries(tasks: Task[], rangeStart: Date, rangeEnd: Date): AgendaEntry[] {
  const entries = tasks.reduce<AgendaEntry[]>((collection, task) => {
    const start = getTaskStart(task);
    if (!start) return collection;
    if (start < rangeStart || start > rangeEnd) return collection;

    collection.push({
      id: `task-${task.id}`,
      sourceId: task.id,
      title: task.title,
      details: task.task_payload,
      start,
      end: getTaskEnd(task, start),
      kind: 'task',
      priority: normalizePriority(task.priority),
      status: normalizeStatus(task.status),
      agent: task.assigned_agent || task.expected_agent || null,
    });

    return collection;
  }, []);

  return sortEntries(entries);
}

function createRecurringEntry(template: RecurringTask, start: Date, end: Date): AgendaEntry {
  return {
    id: `recurring-${template.id}-${start.toISOString()}`,
    sourceId: template.id,
    title: template.title,
    details: template.task_payload,
    start,
    end,
    kind: 'recurring',
    priority: normalizePriority(template.priority),
    status: 'recurring',
    agent: template.expected_agent || null,
  };
}

function hasSpawnedTaskNear(
  tasks: Task[],
  recurringTaskId: number,
  occurrenceStart: Date,
): boolean {
  return tasks.some((task) => {
    if (task.recurring_task_id !== recurringTaskId) return false;
    const taskStart = getTaskStart(task);
    if (!taskStart) return false;
    return Math.abs(taskStart.getTime() - occurrenceStart.getTime()) <= 2 * 60 * 60 * 1000;
  });
}

function buildIntervalOccurrences(
  template: RecurringTask,
  schedule: ScheduleConfig,
  rangeStart: Date,
  rangeEnd: Date,
  tasks: Task[],
): AgendaEntry[] {
  const intervalMinutes = schedule.interval_minutes;
  if (!intervalMinutes || intervalMinutes <= 0) return [];

  const anchor =
    parseMaybeDate(template.last_spawned_at) ||
    parseMaybeDate(template.created_at) ||
    startOfDay(rangeStart);

  const entries: AgendaEntry[] = [];
  let current = new Date(anchor);
  let guard = 0;

  while (current < rangeStart && guard < 200) {
    current = addMinutes(current, intervalMinutes);
    guard += 1;
  }

  while (current <= rangeEnd && guard < 260) {
    if (!hasSpawnedTaskNear(tasks, template.id, current)) {
      entries.push(createRecurringEntry(template, current, addMinutes(current, 60)));
    }
    current = addMinutes(current, intervalMinutes);
    guard += 1;
  }

  return entries;
}

function buildPatternOccurrences(
  template: RecurringTask,
  schedule: ScheduleConfig,
  rangeStart: Date,
  rangeEnd: Date,
  tasks: Task[],
): AgendaEntry[] {
  const targetDays = schedule.days || [];
  const targetHour = schedule.hour ?? 9;
  const targetMinute = schedule.minute ?? 0;
  const entries: AgendaEntry[] = [];

  for (let current = startOfDay(rangeStart); current <= rangeEnd; current = addDays(current, 1)) {
    if (targetDays.length > 0 && !targetDays.includes(toPythonWeekday(current))) {
      continue;
    }

    const occurrenceStart = new Date(
      current.getFullYear(),
      current.getMonth(),
      current.getDate(),
      targetHour,
      targetMinute,
      0,
      0,
    );

    if (occurrenceStart < rangeStart || occurrenceStart > rangeEnd) {
      continue;
    }

    if (hasSpawnedTaskNear(tasks, template.id, occurrenceStart)) {
      continue;
    }

    entries.push(createRecurringEntry(template, occurrenceStart, addMinutes(occurrenceStart, 60)));
  }

  return entries;
}

function buildRecurringEntries(
  recurringTasks: RecurringTask[],
  tasks: Task[],
  rangeStart: Date,
  rangeEnd: Date,
): AgendaEntry[] {
  const entries = recurringTasks.flatMap((template) => {
    const schedule = template.schedule_config || {};
    if (schedule.interval_minutes) {
      return buildIntervalOccurrences(template, schedule, rangeStart, rangeEnd, tasks);
    }
    return buildPatternOccurrences(template, schedule, rangeStart, rangeEnd, tasks);
  });

  return sortEntries(entries);
}

function getAgendaRange(view: AgendaView, referenceDate: Date): { start: Date; end: Date } {
  if (view === 'week') {
    return {
      start: startOfWeek(referenceDate),
      end: endOfWeek(referenceDate),
    };
  }

  if (view === 'schedule') {
    return {
      start: startOfDay(referenceDate),
      end: endOfDay(addDays(referenceDate, SCHEDULE_WINDOW_DAYS - 1)),
    };
  }

  return {
    start: startOfWeek(startOfMonth(referenceDate)),
    end: endOfWeek(endOfMonth(referenceDate)),
  };
}

function formatTime(date: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  }).format(date);
}

function formatMonthLabel(date: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    month: 'long',
    year: 'numeric',
  }).format(date);
}

function formatScheduleDate(date: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
  }).format(date);
}

function formatCompactDate(date: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
  }).format(date);
}

function formatAgentName(agent?: string | null): string {
  if (!agent) return 'Unassigned';
  return agent.charAt(0).toUpperCase() + agent.slice(1);
}

function nextReferenceDate(view: AgendaView, referenceDate: Date): Date {
  if (view === 'month') return addMonths(referenceDate, 1);
  if (view === 'week') return addDays(referenceDate, 7);
  return addDays(referenceDate, SCHEDULE_WINDOW_DAYS);
}

function previousReferenceDate(view: AgendaView, referenceDate: Date): Date {
  if (view === 'month') return addMonths(referenceDate, -1);
  if (view === 'week') return addDays(referenceDate, -7);
  return addDays(referenceDate, -SCHEDULE_WINDOW_DAYS);
}

function groupEntriesByDay(entries: AgendaEntry[]): Array<{ day: Date; entries: AgendaEntry[] }> {
  const groups = new Map<string, { day: Date; entries: AgendaEntry[] }>();

  entries.forEach((entry) => {
    const key = formatDayKey(entry.start);
    const existing = groups.get(key);
    if (existing) {
      existing.entries.push(entry);
      return;
    }
    groups.set(key, { day: startOfDay(entry.start), entries: [entry] });
  });

  return Array.from(groups.values()).sort((left, right) => left.day.getTime() - right.day.getTime());
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function AgendaEntryBadge({ entry }: { entry: AgendaEntry }) {
  const priority = priorityStyles[entry.priority] || priorityStyles.medium;
  const statusClass = statusStyles[entry.status] || statusStyles.queued;
  const time = `${formatTime(entry.start)}${entry.kind === 'task' ? '' : ' · Recurring'}`;

  return (
    <div
      className={`rounded-md border-l-2 ${priority.border} bg-[#181818]/90 px-2.5 py-2 shadow-[0_10px_24px_rgba(0,0,0,0.18)]`}
      title={`${entry.title} · ${time}`}
    >
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${priority.dot}`}></span>
        <p className="truncate font-label text-[10px] uppercase tracking-[0.24em] text-[#b8a6a1]">
          {time}
        </p>
      </div>
      <p className="mt-1 truncate font-body text-sm font-semibold text-[#f4efee]">{entry.title}</p>
      <div className="mt-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em]">
        <span className={`rounded-full px-2 py-1 ${statusClass}`}>{entry.status.replace(/_/g, ' ')}</span>
        <span className="text-[#8f8582]">{formatAgentName(entry.agent)}</span>
      </div>
    </div>
  );
}

function MonthlyView({
  entries,
  referenceDate,
}: {
  entries: AgendaEntry[];
  referenceDate: Date;
}) {
  const gridStart = startOfWeek(startOfMonth(referenceDate));
  const cells = Array.from({ length: 42 }, (_, index) => addDays(gridStart, index));

  return (
    <div className="overflow-x-auto rounded-[28px] border border-white/5 bg-[#141414]/90 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.24)]">
      <div className="grid min-w-[900px] grid-cols-7 gap-2">
        {DAY_LABELS.map((label) => (
          <div key={label} className="px-3 py-2 text-center font-label text-[11px] uppercase tracking-[0.3em] text-[#8f8582]">
            {label}
          </div>
        ))}
        {cells.map((day) => {
          const dayEntries = entries.filter((entry) => isSameDay(entry.start, day)).slice(0, 3);
          const remaining = entries.filter((entry) => isSameDay(entry.start, day)).length - dayEntries.length;

          return (
            <div
              key={day.toISOString()}
              className={`min-h-[152px] rounded-2xl border p-3 transition-colors ${
                isToday(day)
                  ? 'border-[#6e373c] bg-[#241618]/90'
                  : isSameMonth(day, referenceDate)
                    ? 'border-white/5 bg-[#181818]/85'
                    : 'border-white/5 bg-[#111111]/65'
              }`}
            >
              <div className="mb-3 flex items-center justify-between">
                <span className="font-label text-[10px] uppercase tracking-[0.24em] text-[#786f6c]">
                  {formatCompactDate(day)}
                </span>
                <span
                  className={`flex h-8 w-8 items-center justify-center rounded-full font-headline text-sm ${
                    isToday(day) ? 'bg-[#4A0404] text-white' : 'text-[#cfc5c2]'
                  }`}
                >
                  {day.getDate()}
                </span>
              </div>
              <div className="space-y-2">
                {dayEntries.map((entry) => (
                  <AgendaEntryBadge key={entry.id} entry={entry} />
                ))}
                {remaining > 0 && (
                  <p className="px-1 font-label text-[10px] uppercase tracking-[0.22em] text-[#8f8582]">
                    +{remaining} more
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function WeeklyView({
  entries,
  referenceDate,
}: {
  entries: AgendaEntry[];
  referenceDate: Date;
}) {
  const weekStart = startOfWeek(referenceDate);
  const days = Array.from({ length: 7 }, (_, index) => addDays(weekStart, index));
  const totalHeight = (WEEK_HOUR_END - WEEK_HOUR_START) * WEEK_HOUR_HEIGHT;

  return (
    <div className="overflow-x-auto rounded-[28px] border border-white/5 bg-[#141414]/90 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.24)]">
      <div className="min-w-[980px]">
        <div className="grid grid-cols-[72px_repeat(7,minmax(0,1fr))] border-b border-white/5">
          <div className="px-2 py-3"></div>
          {days.map((day) => (
            <div key={day.toISOString()} className="border-l border-white/5 px-3 py-3 text-center">
              <p className="font-label text-[10px] uppercase tracking-[0.24em] text-[#8f8582]">
                {DAY_LABELS[(toPythonWeekday(day) + 7) % 7]}
              </p>
              <p className={`mt-1 font-headline text-lg ${isToday(day) ? 'text-[#ffb3b5]' : 'text-[#f4efee]'}`}>
                {day.getDate()}
              </p>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-[72px_repeat(7,minmax(0,1fr))]">
          <div className="relative" style={{ height: `${totalHeight}px` }}>
            {Array.from({ length: WEEK_HOUR_END - WEEK_HOUR_START }, (_, index) => {
              const hour = WEEK_HOUR_START + index;
              return (
                <div
                  key={hour}
                  className="absolute inset-x-0 border-t border-white/5 pr-3 text-right font-label text-[10px] uppercase tracking-[0.18em] text-[#6f6664]"
                  style={{ top: `${index * WEEK_HOUR_HEIGHT}px` }}
                >
                  {`${hour}:00`}
                </div>
              );
            })}
          </div>
          {days.map((day) => {
            const dayStart = new Date(day.getFullYear(), day.getMonth(), day.getDate(), WEEK_HOUR_START, 0, 0, 0);
            const dayEnd = new Date(day.getFullYear(), day.getMonth(), day.getDate(), WEEK_HOUR_END, 0, 0, 0);
            const dayEntries = entries.filter((entry) => isSameDay(entry.start, day));

            return (
              <div key={day.toISOString()} className="relative border-l border-white/5" style={{ height: `${totalHeight}px` }}>
                {Array.from({ length: WEEK_HOUR_END - WEEK_HOUR_START }, (_, index) => (
                  <div
                    key={index}
                    className="absolute inset-x-0 border-t border-white/5"
                    style={{ top: `${index * WEEK_HOUR_HEIGHT}px` }}
                  ></div>
                ))}
                {dayEntries.map((entry) => {
                  const priority = priorityStyles[entry.priority] || priorityStyles.medium;
                  const eventStart = clamp(
                    (entry.start.getTime() - dayStart.getTime()) / (1000 * 60),
                    0,
                    (WEEK_HOUR_END - WEEK_HOUR_START) * 60,
                  );
                  const eventEnd = clamp(
                    (entry.end.getTime() - dayStart.getTime()) / (1000 * 60),
                    30,
                    (WEEK_HOUR_END - WEEK_HOUR_START) * 60,
                  );
                  const top = (eventStart / 60) * WEEK_HOUR_HEIGHT;
                  const height = Math.max(((eventEnd - eventStart) / 60) * WEEK_HOUR_HEIGHT, 44);

                  if (entry.end < dayStart || entry.start > dayEnd) {
                    return null;
                  }

                  return (
                    <div
                      key={entry.id}
                      className={`absolute left-2 right-2 rounded-xl border-l-4 ${priority.border} bg-[#1a1a1a]/95 px-3 py-2 shadow-[0_10px_26px_rgba(0,0,0,0.2)]`}
                      style={{ top: `${top}px`, height: `${height}px` }}
                    >
                      <p className="truncate font-label text-[10px] uppercase tracking-[0.18em] text-[#8f8582]">
                        {formatTime(entry.start)}
                      </p>
                      <p className="mt-1 truncate font-body text-sm font-semibold text-[#f4efee]">{entry.title}</p>
                      <p className="mt-1 truncate text-[11px] text-[#9e9390]">{formatAgentName(entry.agent)}</p>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function ScheduleView({ entries }: { entries: AgendaEntry[] }) {
  const groups = groupEntriesByDay(entries);

  return (
    <div className="rounded-[28px] border border-white/5 bg-[#141414]/90 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.24)]">
      <div className="space-y-6">
        {groups.length === 0 && (
          <div className="rounded-2xl border border-dashed border-white/10 bg-[#161616] px-6 py-12 text-center">
            <p className="font-headline text-2xl text-[#f4efee]">No scheduled activity in this window</p>
            <p className="mt-2 font-body text-sm text-[#988d89]">
              New task instances and recurring schedules will appear here as the queue fills.
            </p>
          </div>
        )}
        {groups.map((group) => (
          <section key={formatDayKey(group.day)} className="space-y-3">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <div>
                <p className="font-headline text-2xl text-[#f4efee]">{formatScheduleDate(group.day)}</p>
                <p className="mt-1 font-label text-[10px] uppercase tracking-[0.24em] text-[#8f8582]">
                  {group.entries.length} scheduled items
                </p>
              </div>
            </div>
            <div className="space-y-3">
              {group.entries.map((entry) => {
                const priority = priorityStyles[entry.priority] || priorityStyles.medium;
                const statusClass = statusStyles[entry.status] || statusStyles.queued;

                return (
                  <article
                    key={entry.id}
                    className={`rounded-2xl border-l-4 ${priority.border} bg-[#181818]/90 px-5 py-4 shadow-[0_10px_24px_rgba(0,0,0,0.18)]`}
                  >
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="font-headline text-lg text-[#f4efee]">{formatTime(entry.start)}</span>
                      <span className={`rounded-full px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] ${priority.chip}`}>
                        {entry.priority}
                      </span>
                      <span className={`rounded-full px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] ${statusClass}`}>
                        {entry.status.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <h3 className="mt-3 font-headline text-xl text-[#f4efee]">{entry.title}</h3>
                    <p className="mt-2 font-body text-sm leading-6 text-[#9e9390]">{entry.details}</p>
                    <div className="mt-3 flex flex-wrap items-center gap-4 text-[11px] uppercase tracking-[0.18em] text-[#8f8582]">
                      <span>{formatAgentName(entry.agent)}</span>
                      <span>{entry.kind === 'recurring' ? 'Recurring template' : 'Live scheduled task'}</span>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function QueueCard({
  title,
  value,
  description,
}: {
  title: string;
  value: string;
  description: string;
}) {
  return (
    <div className="rounded-[24px] border border-white/5 bg-[#161616]/90 p-5 shadow-[0_16px_60px_rgba(0,0,0,0.18)]">
      <p className="font-label text-[10px] uppercase tracking-[0.28em] text-[#8f8582]">{title}</p>
      <p className="mt-3 font-headline text-3xl text-[#f4efee]">{value}</p>
      <p className="mt-2 font-body text-sm text-[#9e9390]">{description}</p>
    </div>
  );
}

export function Agenda({
  agents,
  actions,
  tasks,
  recurringTasks,
  honorific,
  fullName,
}: AgendaProps) {
  const [view, setView] = useState<AgendaView>('month');
  const [referenceDate, setReferenceDate] = useState(() => new Date());

  const range = getAgendaRange(view, referenceDate);
  const taskEntries = buildTaskEntries(tasks, range.start, range.end);
  const recurringEntries = buildRecurringEntries(recurringTasks, tasks, range.start, range.end);
  const entries = sortEntries([...recurringEntries, ...taskEntries]);

  const upcomingTasks = sortEntries(
    buildTaskEntries(tasks, startOfDay(new Date()), endOfDay(addDays(new Date(), 21))),
  ).filter((entry) => ['queued', 'in_progress', 'drafted'].includes(entry.status));

  const priorityQueue = upcomingTasks.slice(0, 5);
  const activeAgents = new Set(
    upcomingTasks
      .map((entry) => entry.agent)
      .filter((agent): agent is string => Boolean(agent)),
  );
  const recurringThisWeek = buildRecurringEntries(
    recurringTasks,
    tasks,
    startOfWeek(new Date()),
    endOfWeek(new Date()),
  );
  const latestActions = actions.slice(0, 5);

  return (
    <section className="space-y-6">
      <div className="rounded-[32px] border border-white/5 bg-[radial-gradient(circle_at_top_left,_rgba(122,27,34,0.34),_transparent_46%),linear-gradient(180deg,_rgba(23,23,23,0.98),_rgba(17,17,17,0.95))] p-8 shadow-[0_22px_100px_rgba(0,0,0,0.28)]">
        <div className="flex flex-col gap-8 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="font-label text-[10px] uppercase tracking-[0.32em] text-[#8f8582]">
              Home Dashboard · Local Command Schedule
            </p>
            <h2 className="mt-3 font-headline text-5xl tracking-tight text-[#f7f1f0]">The Agenda</h2>
            <p className="mt-3 max-w-2xl font-body text-base leading-7 text-[#b6abaa]">
              Upcoming tasks, recurring agent routines, and the sharpest priorities for {fullName},
              organized in one local-first command view.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setReferenceDate(previousReferenceDate(view, referenceDate))}
              className="rounded-full border border-white/10 bg-[#181818] px-4 py-2 font-label text-[10px] uppercase tracking-[0.22em] text-[#d7cdca] transition hover:border-[#6e373c] hover:text-white"
            >
              Prev
            </button>
            <button
              type="button"
              onClick={() => setReferenceDate(new Date())}
              className="rounded-full bg-[#4A0404] px-4 py-2 font-label text-[10px] uppercase tracking-[0.22em] text-white transition hover:brightness-110"
            >
              Today
            </button>
            <button
              type="button"
              onClick={() => setReferenceDate(nextReferenceDate(view, referenceDate))}
              className="rounded-full border border-white/10 bg-[#181818] px-4 py-2 font-label text-[10px] uppercase tracking-[0.22em] text-[#d7cdca] transition hover:border-[#6e373c] hover:text-white"
            >
              Next
            </button>
          </div>
        </div>

        <div className="mt-8 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <p className="font-headline text-2xl text-[#f4efee]">{formatMonthLabel(referenceDate)}</p>
          <div className="inline-flex rounded-full border border-white/10 bg-[#151515]/90 p-1">
            {VIEW_OPTIONS.map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => setView(option.id)}
                className={`rounded-full px-4 py-2 font-label text-[10px] uppercase tracking-[0.24em] transition ${
                  view === option.id
                    ? 'bg-[#f4efee] text-[#131313]'
                    : 'text-[#9e9390] hover:text-[#f4efee]'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <QueueCard
          title="Open Queue"
          value={`${upcomingTasks.length}`}
          description="Scheduled task instances waiting to be picked up, completed, or reviewed."
        />
        <QueueCard
          title="Recurring This Week"
          value={`${recurringThisWeek.length}`}
          description="Autonomous routines forecasted from local recurring templates in the current week."
        />
        <QueueCard
          title="Agents Engaged"
          value={`${activeAgents.size || agents.filter((agent) => agent.is_active).length}`}
          description="Family members with assigned work or recent signal across the current agenda."
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div>
          {view === 'month' && <MonthlyView entries={entries} referenceDate={referenceDate} />}
          {view === 'week' && <WeeklyView entries={entries} referenceDate={referenceDate} />}
          {view === 'schedule' && <ScheduleView entries={entries} />}
        </div>

        <aside className="space-y-5">
          <div className="rounded-[28px] border border-white/5 bg-[#151515]/92 p-5 shadow-[0_18px_70px_rgba(0,0,0,0.2)]">
            <div className="flex items-center justify-between">
              <h3 className="font-headline text-2xl text-[#f4efee]">Key Priorities</h3>
              <span className="font-label text-[10px] uppercase tracking-[0.24em] text-[#8f8582]">Next Up</span>
            </div>
            <div className="mt-4 space-y-3">
              {priorityQueue.length === 0 && (
                <p className="rounded-2xl border border-dashed border-white/10 bg-[#171717] px-4 py-6 font-body text-sm text-[#988d89]">
                  The queue is clear right now. New priorities will surface here as soon as local tasks are created.
                </p>
              )}
              {priorityQueue.map((entry) => {
                const priority = priorityStyles[entry.priority] || priorityStyles.medium;
                return (
                  <div key={entry.id} className="rounded-2xl border border-white/5 bg-[#191919] p-4">
                    <div className="flex items-center justify-between gap-3">
                      <span className={`rounded-full px-2.5 py-1 text-[10px] uppercase tracking-[0.18em] ${priority.chip}`}>
                        {entry.priority}
                      </span>
                      <span className="font-label text-[10px] uppercase tracking-[0.18em] text-[#8f8582]">
                        {formatCompactDate(entry.start)}
                      </span>
                    </div>
                    <p className="mt-3 font-body text-sm font-semibold text-[#f4efee]">{entry.title}</p>
                    <p className="mt-2 text-[11px] uppercase tracking-[0.18em] text-[#8f8582]">
                      {formatTime(entry.start)} · {formatAgentName(entry.agent)}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-[28px] border border-white/5 bg-[#151515]/92 p-5 shadow-[0_18px_70px_rgba(0,0,0,0.2)]">
            <div className="flex items-center justify-between">
              <h3 className="font-headline text-2xl text-[#f4efee]">Agent Cadence</h3>
              <span className="font-label text-[10px] uppercase tracking-[0.24em] text-[#8f8582]">Scheduled</span>
            </div>
            <div className="mt-4 space-y-3">
              {agents.map((agent) => {
                const load = upcomingTasks.filter((entry) => entry.agent?.toLowerCase() === (agent.name || "").toLowerCase()).length;
                const recurringLoad = recurringThisWeek.filter(
                  (entry) => entry.agent?.toLowerCase() === (agent.name || "").toLowerCase(),
                ).length;

                return (
                  <div key={agent.name} className="rounded-2xl border border-white/5 bg-[#191919] p-4">
                    <div className="flex items-center justify-between">
                      <p className="font-body text-sm font-semibold capitalize text-[#f4efee]">{agent.name}</p>
                      <span className="font-label text-[10px] uppercase tracking-[0.18em] text-[#8f8582]">
                        {load + recurringLoad} items
                      </span>
                    </div>
                    <div className="mt-3 flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-[#8f8582]">
                      <span>{load} live</span>
                      <span className="text-[#4f4947]">•</span>
                      <span>{recurringLoad} recurring</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-[28px] border border-white/5 bg-[#151515]/92 p-5 shadow-[0_18px_70px_rgba(0,0,0,0.2)]">
            <div className="flex items-center justify-between">
              <h3 className="font-headline text-2xl text-[#f4efee]">Recent Activity</h3>
              <span className="font-label text-[10px] uppercase tracking-[0.24em] text-[#8f8582]">Local Log</span>
            </div>
            <div className="mt-4 space-y-3">
              {latestActions.length === 0 && (
                <p className="rounded-2xl border border-dashed border-white/10 bg-[#171717] px-4 py-6 font-body text-sm text-[#988d89]">
                  No recent agent actions have been recorded yet.
                </p>
              )}
              {latestActions.map((action) => {
                const actionDate = parseMaybeDate(action.timestamp);
                return (
                  <div key={action.id} className="rounded-2xl border border-white/5 bg-[#191919] p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-body text-sm font-semibold capitalize text-[#f4efee]">{action.agent_name}</p>
                      <span className="font-label text-[10px] uppercase tracking-[0.18em] text-[#8f8582]">
                        {actionDate ? formatTime(actionDate) : 'Unknown'}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-[#b7acab]">{action.action_type.replace(/_/g, ' ')}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}

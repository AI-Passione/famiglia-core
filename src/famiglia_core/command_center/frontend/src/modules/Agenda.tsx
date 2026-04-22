import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import type { FamigliaAgent, ActionLog, RecurringTask, ScheduleConfig, Task, GraphDefinition, AgendaEntry } from '../types';
import { AgendaEventModal } from './ui/AgendaEventModal';

type AgendaView = 'schedule' | 'week' | 'month';

interface AgendaProps {
  agents: FamigliaAgent[];
  actions: ActionLog[];
  tasks: Task[];
  recurringTasks: RecurringTask[];
  honorific: string;
  fullName: string;
  graphs: GraphDefinition[];
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

function isBefore(left: Date, right: Date): boolean {
  return left.getTime() < right.getTime();
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

function AgendaEntryBadge({ entry, onClick, isPast }: { entry: AgendaEntry; onClick?: () => void; isPast?: boolean }) {
  const priority = priorityStyles[entry.priority] || priorityStyles.medium;
  const statusClass = statusStyles[entry.status] || statusStyles.queued;
  const time = `${formatTime(entry.start)}${entry.kind === 'task' ? '' : ' · Recurring'}`;

  return (
    <div
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
      className={`rounded-md border-l-2 ${priority.border} bg-[#181818]/90 px-2.5 py-2 shadow-[0_10px_24px_rgba(0,0,0,0.18)] cursor-pointer hover:bg-[#222222] transition-all ${isPast ? 'opacity-40 grayscale hover:opacity-100 hover:grayscale-0' : ''}`}
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
  onEventClick,
  onCreateEvent,
  now,
}: {
  entries: AgendaEntry[];
  referenceDate: Date;
  onEventClick: (entry: AgendaEntry) => void;
  onCreateEvent: (date: Date) => void;
  now: Date;
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
          const allDayEntries = entries.filter((entry) => isSameDay(entry.start, day));
          const dayEntries = allDayEntries.slice(0, 6);
          const remaining = allDayEntries.length - dayEntries.length;

          return (
            <div
              key={day.toISOString()}
              onClick={() => onCreateEvent(day)}
              className={`min-h-[152px] flex flex-col rounded-2xl border p-3 transition-colors cursor-pointer group ${
                isToday(day)
                  ? 'border-[#6e373c] bg-[#241618]/90'
                  : isSameMonth(day, referenceDate)
                    ? (isBefore(day, startOfDay(now)) ? 'border-white/5 bg-black/40' : 'border-white/5 bg-[#181818]/85 hover:bg-[#1a1a1a]')
                    : 'border-white/5 bg-[#111111]/65'
              }`}
            >
              <div className="mb-3 flex items-center justify-between shrink-0">
                <span className="font-label text-[10px] uppercase tracking-[0.24em] text-[#786f6c]">
                  {formatCompactDate(day)}
                </span>
                <span
                  className={`flex h-8 w-8 items-center justify-center rounded-full font-headline text-sm transition-transform group-hover:scale-110 ${
                    isToday(day) ? 'bg-[#4A0404] text-white' : 'text-[#cfc5c2]'
                  }`}
                >
                  {day.getDate()}
                </span>
              </div>
              <div className="flex-1 overflow-y-auto space-y-2 custom-scrollbar pr-1">
                {dayEntries.map((entry) => {
                  const isPast = entry.end.getTime() < now.getTime() && !isSameDay(entry.end, now);
                  return (
                    <div key={entry.id} className={isPast ? 'opacity-40 grayscale' : ''}>
                      <AgendaEntryBadge entry={entry} onClick={() => onEventClick(entry)} isPast={isPast} />
                    </div>
                  );
                })}
                {remaining > 0 && (
                  <p className="px-1 py-1 font-label text-[9px] uppercase tracking-[0.22em] text-[#8f8582] bg-white/5 rounded-md text-center">
                    +{remaining} more directives
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
  onEventClick,
  onCreateEvent,
  now,
}: {
  entries: AgendaEntry[];
  referenceDate: Date;
  onEventClick: (entry: AgendaEntry) => void;
  onCreateEvent: (date: Date) => void;
  now: Date;
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

            const isPastDay = isBefore(day, startOfDay(now));

            return (
              <div 
                key={day.toISOString()} 
                className={`relative border-l border-white/5 ${isPastDay ? 'bg-black/40' : ''}`} 
                style={{ height: `${totalHeight}px` }}
              >
                {Array.from({ length: WEEK_HOUR_END - WEEK_HOUR_START }, (_, index) => (
                  <div
                    key={index}
                    onClick={(e) => {
                      e.stopPropagation();
                      const clickDate = new Date(day);
                      clickDate.setHours(WEEK_HOUR_START + index, 0, 0, 0);
                      onCreateEvent(clickDate);
                    }}
                    className="absolute inset-x-0 border-t border-white/5 hover:bg-white/[0.02] cursor-pointer transition-colors"
                    style={{ top: `${index * WEEK_HOUR_HEIGHT}px`, height: `${WEEK_HOUR_HEIGHT}px` }}
                  ></div>
                ))}
                
                {/* Current Time Indicator */}
                {isToday(day) && (
                  (() => {
                    const nowMinutes = (now.getHours() * 60 + now.getMinutes()) - (WEEK_HOUR_START * 60);
                    const nowPos = (nowMinutes / 60) * WEEK_HOUR_HEIGHT;
                    if (nowPos >= 0 && nowPos <= totalHeight) {
                      return (
                        <div 
                          className="absolute inset-x-0 z-20 flex items-center" 
                          style={{ top: `${nowPos}px` }}
                        >
                          <div className="h-[2px] flex-1 bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]" />
                          <div className="h-2 w-2 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)] -ml-1" />
                        </div>
                      );
                    }
                    return null;
                  })()
                )}

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

                  const isPast = entry.end.getTime() < now.getTime() && !isSameDay(entry.end, now);

                  return (
                    <div
                      key={entry.id}
                      onClick={() => onEventClick(entry)}
                      className={`absolute left-2 right-2 rounded-xl border-l-4 ${priority.border} bg-[#1a1a1a]/95 px-3 py-2 shadow-[0_10px_26px_rgba(0,0,0,0.2)] cursor-pointer hover:bg-[#222222] transition-all overflow-hidden ${isPast ? 'opacity-40 grayscale border-l-outline/30 hover:opacity-100 hover:grayscale-0' : ''}`}
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

function ScheduleView({ entries, onEventClick, now }: { entries: AgendaEntry[]; onEventClick: (entry: AgendaEntry) => void; now: Date }) {
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

                const isPast = entry.end < now && !isSameDay(entry.end, now);
                return (
                  <article
                    key={entry.id}
                    onClick={() => onEventClick(entry)}
                    className={`rounded-2xl border-l-4 ${priority.border} bg-[#181818]/90 px-5 py-4 shadow-[0_10px_24px_rgba(0,0,0,0.18)] cursor-pointer hover:bg-[#222222] transition-all ${isPast ? 'opacity-40 grayscale border-l-outline/30 hover:opacity-100 hover:grayscale-0' : ''}`}
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
  graphs,
}: AgendaProps) {
  const navigate = useNavigate();
  const [view, setView] = useState<AgendaView>('month');
  const [referenceDate, setReferenceDate] = useState(() => new Date());
  const [selectedEntry, setSelectedEntry] = useState<AgendaEntry | null>(null);
  const [now, setNow] = useState(() => new Date());

  const [isEventModalOpen, setEventModalOpen] = useState(false);
  const [modalInitialEntry, setModalInitialEntry] = useState<AgendaEntry | null>(null);
  const [modalInitialDate, setModalInitialDate] = useState<Date | null>(null);

  useEffect(() => {
    const timer = setInterval(() => {
      setNow(new Date());
    }, 30000); // Update every 30s for smoothness
    return () => clearInterval(timer);
  }, []);

  const handleEventClick = (entry: AgendaEntry) => {
    console.log("[Agenda] Event clicked:", entry);
    setSelectedEntry(entry);
  };

  const handleEditEvent = (entry: AgendaEntry) => {
    setModalInitialEntry(entry);
    setModalInitialDate(null);
    setEventModalOpen(true);
    setSelectedEntry(null);
  };

  const handleCreateEvent = (date: Date = new Date()) => {
    setModalInitialEntry(null);
    setModalInitialDate(date);
    setEventModalOpen(true);
  };

  const range = getAgendaRange(view, referenceDate);
  // Expand range for Monthly view to cover the full 42-cell grid
  const fetchRange = view === 'month' 
    ? { start: startOfWeek(startOfMonth(referenceDate)), end: addDays(startOfWeek(startOfMonth(referenceDate)), 42) }
    : range;

  const taskEntries = buildTaskEntries(tasks, fetchRange.start, fetchRange.end);
  const recurringEntries = buildRecurringEntries(recurringTasks, tasks, range.start, range.end);
  const entries = sortEntries([...recurringEntries, ...taskEntries]);

  // Debug logging to help identify why tasks might be missing
  useEffect(() => {
    console.log(`[Agenda Debug] Rendering view: ${view}`);
    console.log(`[Agenda Debug] Reference Date: ${referenceDate.toISOString()}`);
    console.log(`[Agenda Debug] Total Tasks from App: ${tasks.length}`);
    console.log(`[Agenda Debug] Tasks in current range: ${taskEntries.length}`);
    if (taskEntries.length > 0) {
      console.log(`[Agenda Debug] Sample Task Date: ${taskEntries[0].start.toISOString()}`);
    }
  }, [view, referenceDate, tasks.length, taskEntries.length]);

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
          <div className="space-y-2">
            <div className="flex items-center gap-4">
              <h2 className="font-headline text-5xl font-bold tracking-tight text-[#f4efee]">
                Agenda
              </h2>
              <div className="mt-2 rounded-full bg-white/5 px-4 py-1 font-label text-[10px] uppercase tracking-[0.3em] text-[#8f8582]">
                Last Synced: {now.toLocaleTimeString()}
              </div>
            </div>
            <p className="font-body text-lg text-[#8f8582]">
              Commanding the temporal flow for {honorific} {fullName}.
            </p>
            <div className="mt-6 flex gap-4">
              <button
                onClick={() => handleCreateEvent()}
                className="flex items-center gap-2 rounded-full bg-[#6e373c] px-6 py-3 font-label text-[10px] uppercase tracking-[0.24em] text-white shadow-[0_12px_40px_rgba(110,55,60,0.3)] transition hover:bg-[#8e474c] hover:scale-105 active:scale-95"
              >
                <span className="material-symbols-outlined text-[18px]">add_task</span>
                Schedule New Directive
              </button>
            </div>
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
          {view === 'month' && <MonthlyView entries={entries} referenceDate={referenceDate} onEventClick={handleEventClick} onCreateEvent={handleCreateEvent} now={now} />}
          {view === 'week' && <WeeklyView entries={entries} referenceDate={referenceDate} onEventClick={handleEventClick} onCreateEvent={handleCreateEvent} now={now} />}
          {view === 'schedule' && <ScheduleView entries={entries} onEventClick={handleEventClick} now={now} />}
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
                const isPast = entry.end.getTime() < now.getTime() && !isSameDay(entry.end, now);
                return (
                  <div 
                    key={entry.id} 
                    onClick={() => handleEventClick(entry)}
                    className={`rounded-2xl border-l-4 border-white/5 bg-[#191919] p-4 cursor-pointer hover:bg-[#222222] transition-all ${isPast ? 'opacity-40 grayscale hover:opacity-100 hover:grayscale-0' : ''}`}
                  >
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
                // Try to find a matching task if it exists
                const matchingTask = tasks.find(t => t.id === action.action_details?.task_id);
                
                return (
                  <div 
                    key={action.id} 
                    onClick={() => {
                      if (matchingTask) {
                        const entry = buildTaskEntries([matchingTask], startOfDay(new Date(action.timestamp)), endOfDay(new Date(action.timestamp)))[0];
                        if (entry) handleEventClick(entry);
                      }
                    }}
                    className={`rounded-2xl border border-white/5 bg-[#191919] p-4 ${matchingTask ? 'cursor-pointer hover:bg-[#222222] transition-colors' : ''}`}
                  >
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
      <AnimatePresence>
        {selectedEntry && (
          <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedEntry(null)}
              className="absolute inset-0 bg-black/80 backdrop-blur-md"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 40 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 40 }}
              className="relative w-full max-w-lg overflow-hidden rounded-[32px] border border-white/10 bg-[#161616] shadow-[0_32px_120px_rgba(0,0,0,0.6)]"
            >
              {/* Header Accent */}
              <div 
                className="h-2" 
                style={{ backgroundColor: selectedEntry.priority === 'critical' ? '#ff7f88' : selectedEntry.priority === 'high' ? '#ffb46b' : selectedEntry.priority === 'low' ? '#87d89b' : '#6bc7ff' }} 
              />
              
              <div className="p-8">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <p className="font-label text-[10px] uppercase tracking-[0.4em] text-[#8f8582]">
                      {selectedEntry.kind === 'task' ? 'Local Directive' : 'Recurring Routine'}
                    </p>
                    <h3 className="font-headline text-3xl text-[#f4efee]">{selectedEntry.title}</h3>
                  </div>
                  <button
                    onClick={() => setSelectedEntry(null)}
                    className="flex h-10 w-10 items-center justify-center rounded-full bg-white/5 text-[#8f8582] transition hover:bg-white/10 hover:text-white"
                  >
                    <span className="material-symbols-outlined">close</span>
                  </button>
                </div>

                <div className="mt-8 space-y-8">
                   <div className="grid grid-cols-2 gap-4">
                      <div className="rounded-2xl bg-white/[0.03] p-5 border border-white/5">
                        <p className="font-label text-[9px] uppercase tracking-widest text-[#6f6664]">Scheduled For</p>
                        <p className="mt-2 font-headline text-xl text-[#f4efee]">{formatTime(selectedEntry.start)}</p>
                        <p className="mt-1 font-body text-xs text-[#8f8582]">{formatScheduleDate(selectedEntry.start)}</p>
                      </div>
                      <div className="rounded-2xl bg-white/[0.03] p-5 border border-white/5">
                        <p className="font-label text-[9px] uppercase tracking-widest text-[#6f6664]">Agent Assigned</p>
                        <p className="mt-2 font-headline text-xl text-[#f4efee]">{formatAgentName(selectedEntry.agent)}</p>
                        <p className="mt-1 font-body text-xs text-[#8f8582]">Autonomous Executor</p>
                      </div>
                   </div>

                   <div className="space-y-3">
                     <p className="font-label text-[9px] uppercase tracking-widest text-[#6f6664]">Directive Payload</p>
                     <div className="rounded-2xl border border-white/5 bg-black/40 p-6 shadow-inner">
                       <p className="font-body text-sm leading-relaxed text-[#b6abaa] whitespace-pre-wrap italic">
                         "{selectedEntry.details}"
                       </p>
                     </div>
                   </div>

                   <div className="flex items-center justify-between gap-4 pt-4 border-t border-white/5">
                      <div className="flex items-center gap-3">
                         <span className={`rounded-full px-3 py-1.5 text-[10px] uppercase tracking-[0.24em] ${statusStyles[selectedEntry.status]}`}>
                            {selectedEntry.status.replace(/_/g, ' ')}
                         </span>
                         <span className={`rounded-full px-3 py-1.5 text-[10px] uppercase tracking-[0.24em] ${priorityStyles[selectedEntry.priority]?.chip}`}>
                            {selectedEntry.priority}
                         </span>
                      </div>
                      
                      {selectedEntry.kind === 'task' && (
                        <div className="flex gap-3">
                          <button
                            onClick={() => handleEditEvent(selectedEntry)}
                            className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-6 py-3 font-label text-[10px] uppercase tracking-[0.24em] text-white transition hover:bg-white/10"
                          >
                            <span className="material-symbols-outlined text-sm">edit</span>
                            Refine
                          </button>
                          <button
                            onClick={() => {
                              setSelectedEntry(null);
                              navigate(`/operations/tasks/${selectedEntry.sourceId}`);
                            }}
                            className="flex items-center gap-2 rounded-full bg-[#4A0404] px-6 py-3 font-label text-[10px] uppercase tracking-[0.24em] text-white transition hover:brightness-110 shadow-[0_10px_20px_rgba(74,4,4,0.3)]"
                          >
                            View Mission Log
                            <span className="material-symbols-outlined text-sm">arrow_forward</span>
                          </button>
                        </div>
                      )}
                   </div>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <AgendaEventModal
        isOpen={isEventModalOpen}
        onClose={() => setEventModalOpen(false)}
        onSuccess={() => {
          // Data will refresh via the interval in App.tsx
        }}
        agents={agents}
        graphs={graphs}
        initialEntry={modalInitialEntry}
        initialDate={modalInitialDate}
      />
    </section>
  );
}

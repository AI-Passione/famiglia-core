import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MemoryRouter } from 'react-router-dom';
import { Agenda } from '@/modules/Agenda';
import type { FamigliaAgent, ActionLog, RecurringTask, Task } from '@/types';

const agents: any[] = [
  { name: 'alfredo', last_active: '2026-04-01T08:00:00Z', msg_count: 12, status: 'idle', is_active: true },
  { name: 'rossini', last_active: '2026-04-01T07:30:00Z', msg_count: 9, status: 'thinking', is_active: true },
];

const actions: any[] = [
  {
    id: 1,
    timestamp: '2026-04-01T07:45:00Z',
    agent_name: 'alfredo',
    action_type: 'priority_brief',
    action_details: null,
    approval_status: 'approved',
  },
];

const tasks: Task[] = [
  {
    id: 14,
    title: 'Investor prep',
    task_payload: 'Assemble the board-ready briefing packet.',
    status: 'queued',
    priority: 'high',
    expected_agent: 'alfredo',
    eta_pickup_at: '2026-04-02T09:00:00Z',
    eta_completion_at: '2026-04-02T10:30:00Z',
    created_at: '2026-04-01T08:00:00Z',
  },
];

const recurringTasks: RecurringTask[] = [
  {
    id: 21,
    title: 'Weekly executive sweep',
    task_payload: 'Review open priorities and redistribute ownership.',
    priority: 'medium',
    expected_agent: 'rossini',
    schedule_config: { days: [3], hour: 11, minute: 0 },
    last_spawned_at: '2026-03-26T11:00:00Z',
    created_at: '2026-03-01T09:00:00Z',
    updated_at: '2026-03-26T11:00:00Z',
  },
];

describe('Agenda Module', () => {
  it('renders the agenda shell and defaults to monthly view', () => {
    render(
      <MemoryRouter>
        <Agenda
          agents={agents}
          actions={actions}
          tasks={tasks}
          recurringTasks={recurringTasks}
          honorific="Don"
          fullName="Jimmy"
        />
      </MemoryRouter>
    );

    expect(screen.getByText('The Agenda')).toBeDefined();
    expect(screen.getByRole('button', { name: 'Monthly' })).toBeDefined();
    expect(screen.getByText('Key Priorities')).toBeDefined();
    expect(screen.getByText('Agent Cadence')).toBeDefined();
  });

  it('switches between monthly, weekly, and schedule modes', () => {
    render(
      <MemoryRouter>
        <Agenda
          agents={agents}
          actions={actions}
          tasks={tasks}
          recurringTasks={recurringTasks}
          honorific="Don"
          fullName="Jimmy"
        />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Weekly' }));
    expect(screen.getByText('6:00')).toBeDefined();

    fireEvent.click(screen.getByRole('button', { name: 'Schedule' }));
    expect(screen.getAllByText(/scheduled items/i).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: 'Monthly' }));
    expect(screen.getByText('Recent Activity')).toBeDefined();
  });
});

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SituationRoom } from '@/modules/SituationRoom';
import { TerminalProvider } from '@/modules/TerminalContext';
import React from 'react';
import type { Task, ActionLog, GraphDefinition } from '@/types';

// Mock charts if any complex libs are used, but we are using pure tailwind/framer-motion
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    AnimatePresence: ({ children }: any) => <>{children}</>,
    motion: {
      div: require('react').forwardRef(({ children, ...props }: any, ref: any) => {
        const { initial, animate, exit, transition, ...rest } = props;
        return <div ref={ref} {...rest}>{children}</div>;
      }),
      button: require('react').forwardRef(({ children, ...props }: any, ref: any) => {
        const { initial, animate, exit, transition, ...rest } = props;
        return <button ref={ref} {...rest}>{children}</button>;
      }),
    },
  };
});

describe('SituationRoom Component & New Widgets', () => {
  const mockTasks: Task[] = [
    { id: 1, title: 'Clean DB', task_payload: 'Remove orphans', status: 'completed', priority: 'high', created_at: new Date().toISOString(), result_summary: 'DB is clean' },
    { id: 2, title: 'Scrape Web', task_payload: 'Gather intel', status: 'failed', priority: 'low', created_at: new Date().toISOString() },
  ];
  const mockActions: ActionLog[] = [
    { id: 1, timestamp: new Date().toISOString(), agent_name: 'alfredo', action_type: 'System optimized', action_details: null, approval_status: null, completed_at: null, cost_usd: 0, duration_seconds: 0 },
  ];
  const mockGraphs: GraphDefinition[] = [
    { id: 'cleanup-ops', name: 'Cleanup Operations', nodes: [], edges: [] },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/insights')) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            { id: 1, title: 'Market Up', rossini_tldr: 'Buy now' },
            { id: 2, title: 'Market Down', rossini_tldr: 'Hold' },
          ]
        });
      }
      if (url.includes('/operations/graphs/cleanup-ops/execute')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ message: 'Directive Executed Test' })
        });
      }
      return Promise.resolve({ ok: true, json: async () => [] });
    });
  });

  it('renders all main widgets successfully', async () => {
    render(
      <TerminalProvider>
        <SituationRoom
          agents={[]}
          actions={mockActions}
          tasks={mockTasks}
          graphs={mockGraphs}
          honorific="Don Jimmy"
        />
      </TerminalProvider>
    );

    // InsightsTicker should be present
    expect(screen.getByText('Market & Intel Pulse')).toBeDefined();
    
    // LatestMissions should be present
    expect(screen.getByText('Mission Outcomes')).toBeDefined();
    expect(screen.getByText('Clean DB')).toBeDefined();
    
    // OperationsHub should be present
    expect(screen.getByText('Actionable Directives')).toBeDefined();
    expect(screen.getByText('Cleanup Operations')).toBeDefined();
    
    // IntelligenceFeed should be present
    expect(screen.getByText(/Intelligence Feed/i)).toBeDefined();
    expect(screen.getByText(/alfredo:/i)).toBeDefined();
  });

  it('InsightsTicker fetches and displays insights', async () => {
    render(
      <TerminalProvider>
        <SituationRoom agents={[]} actions={[]} tasks={[]} honorific="Don" />
      </TerminalProvider>
    );
    await waitFor(() => {
      expect(screen.getByText('Market Up')).toBeDefined();
      expect(screen.getByText('"Buy now"')).toBeDefined();
    });
  });

  it('OperationsHub triggers execute correctly', async () => {
    render(
      <TerminalProvider>
        <SituationRoom agents={[]} actions={[]} tasks={[]} graphs={mockGraphs} honorific="Don" />
      </TerminalProvider>
    );
    
    const executeBtn = screen.getByText('Execute').closest('button');
    expect(executeBtn).not.toBeNull();
    
    fireEvent.click(executeBtn!);
    
    await waitFor(() => {
      expect(screen.getByText('Directive Executed Test')).toBeDefined();
    });
  });
});

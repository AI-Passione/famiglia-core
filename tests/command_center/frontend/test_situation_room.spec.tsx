import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SituationRoom } from '@/modules/SituationRoom';
import { TerminalProvider } from '@/modules/TerminalContext';
import React from 'react';
import type { Task, ActionLog, GraphDefinition } from '@/types';

// Mocking of framer-motion is handled globally in vitest.setup.ts

describe('SituationRoom Component & New Widgets', () => {
  const mockTasks: Task[] = [
    { id: 1, title: 'Database Analysis', task_payload: 'Remove orphans', status: 'completed', priority: 'high', created_at: new Date().toISOString(), result_summary: 'DB is clean' },
    { id: 2, title: 'Market Research', task_payload: 'Gather intel', status: 'failed', priority: 'low', created_at: new Date().toISOString() },
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
          actions={mockActions}
          tasks={mockTasks}
          graphs={mockGraphs}
          honorific="Don Jimmy"
        />
      </TerminalProvider>
    );

    // Pulse BANs should be present
    expect(screen.getByText('Pulse')).toBeDefined();

    // Mission Outcomes (now inside OpsPulse) should be present
    expect(screen.getByText('Mission Outcomes')).toBeDefined();
    expect(screen.getByText('Database Analysis')).toBeDefined();
    
    // OperationsHub (Awaiting Your Decision + Execute Directive sections)
    expect(screen.getAllByText('Execute Directive').length).toBeGreaterThan(0);
    
    // IntelligenceFeed should be present
    expect(screen.getByText(/Intelligence Feed/i)).toBeDefined();
    expect(screen.getByText(/alfredo:/i)).toBeDefined();
  });

  it('InsightsTicker fetches and displays insights', async () => {
    render(
      <TerminalProvider>
        <SituationRoom actions={[]} tasks={[]} honorific="Don" />
      </TerminalProvider>
    );
    await waitFor(() => {
      expect(screen.getByText('Market Up')).toBeDefined();
      expect(screen.getByText('"Buy now"')).toBeDefined();
    });
  });

  it('OperationsHub triggers execute correctly', async () => {
    const mockExecute = vi.fn();
    render(
      <TerminalProvider>
        <SituationRoom actions={[]} tasks={[]} graphs={mockGraphs} honorific="Don" onExecuteDirective={mockExecute} />
      </TerminalProvider>
    );
    
    // The button text is "Execute Directive" (with a bolt icon span before it)
    const executeBtn = screen.getAllByText('Execute Directive')[0].closest('button');
    expect(executeBtn).not.toBeNull();
    
    fireEvent.click(executeBtn!);
    
    // Clicking the button should invoke the handler passed as prop
    expect(mockExecute).toHaveBeenCalledTimes(1);
  });
});

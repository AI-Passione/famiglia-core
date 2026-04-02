import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Operations } from '@/modules/Operations';
import type { GraphDefinition, Task, ActionLog } from '@/types';
import React from 'react';

const mockGraphs: GraphDefinition[] = [
  { id: '1', name: 'Strategic Core', nodes: [], edges: [] }
];

const mockActions: ActionLog[] = [
  { id: '1', agent_name: 'Don', action_type: 'Decision', action_details: {}, timestamp: new Date().toISOString() }
];

describe('Operations Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url.includes('/actions')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ actions: mockActions, total: 1 }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => [] });
    }));
  });

  it('renders correctly with no selected graph', async () => {
    render(<Operations graphs={mockGraphs} selectedGraph={null} setSelectedGraph={vi.fn()} initialTasks={[]} />);
    
    expect(await screen.findByText(/Operational Pipelines/i)).toBeDefined();
    
    // Check for tripartite section headers via test-id
    expect(await screen.findByTestId('strategic-dialogue-header')).toBeDefined();
    expect(await screen.findByTestId('mission-logs-header')).toBeDefined();
    expect(await screen.findByTestId('tool-ledger-header')).toBeDefined();
  });

  it('fetches and displays tripartite feeds when a graph is selected', async () => {
    render(<Operations graphs={mockGraphs} selectedGraph={mockGraphs[0]} setSelectedGraph={vi.fn()} initialTasks={[]} />);
    
    // Check main title
    expect(await screen.findByTestId('mission-command-header')).toBeDefined();
    
    // Wait for actions to load in the ledger
    await waitFor(() => {
      expect(screen.queryByText(/Decision/i)).toBeTruthy();
      expect(screen.queryByText(/Don/i)).toBeTruthy();
    }, { timeout: 3000 });
  });
});

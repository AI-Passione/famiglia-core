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

const mockMissionLogs = [
  { id: 'ML-001', graph_id: 'strategic_core', timestamp: '2023-10-27 10:00:00', status: 'success', duration: '5.2s', initiator: 'Don' }
];

const mockConversations = [
  { id: 1, conversation_key: 'web:dash:direct:1', updated_at: new Date().toISOString(), latest_message: 'Finalizing strategy...', latest_agent: 'Alfredo' }
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
      if (url.includes('/operations/mission-logs/all')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockMissionLogs,
        });
      }
      if (url.includes('/chat/conversations')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockConversations,
        });
      }
      return Promise.resolve({ ok: true, json: async () => [] });
    }));
  });

  it('renders correctly with tripartite situational feeds', async () => {
    render(<Operations graphs={mockGraphs} selectedGraph={null} setSelectedGraph={vi.fn()} initialTasks={[]} />);
    
    expect(await screen.findByText(/Operational Pipelines/i)).toBeDefined();
    
    // Check for tripartite section headers via test-id
    expect(await screen.findByTestId('mission-logs-header')).toBeDefined();
    expect(await screen.findByTestId('strategic-dialogue-header')).toBeDefined();
    expect(await screen.findByTestId('tool-ledger-header')).toBeDefined();
  });

  it('populates mission logs and strategic dialogue with real-time data', async () => {
    render(<Operations graphs={mockGraphs} selectedGraph={mockGraphs[0]} setSelectedGraph={vi.fn()} initialTasks={[]} />);
    
    // Mission Logs check
    await waitFor(() => {
      expect(screen.queryByText(/strategic_core/i)).toBeTruthy();
      expect(screen.queryByText(/ML-001/i)).toBeTruthy();
    }, { timeout: 3000 });

    // Strategic Dialogue check
    await waitFor(() => {
      expect(screen.queryByText(/Alfredo/i)).toBeTruthy();
      expect(screen.queryByText(/Finalizing strategy/i)).toBeTruthy();
    }, { timeout: 3000 });
    
    // Tool Ledger check
    await waitFor(() => {
      expect(screen.queryByText(/Decision/i)).toBeTruthy();
    }, { timeout: 3000 });
  });
});

import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Operations } from '@/modules/Operations';
import type { GraphDefinition } from '@/types';
import React from 'react';

const mockGraphs: GraphDefinition[] = [
  {
    id: 'market_research',
    name: 'Market Research',
    nodes: [],
    edges: []
  }
];

describe('Operations Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      // Default mock implementation
      if (url.includes('/actions')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ actions: [], total: 0 }),
        });
      }
      if (url.includes('/conversations')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ conversations: [], total: 0 }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ tasks: [], total: 0 }),
      });
    }));
  });

  it('renders correctly with no selected graph', () => {
    render(<Operations graphs={mockGraphs} selectedGraph={null} setSelectedGraph={vi.fn()} initialTasks={[]} />);
    expect(screen.getByText('Operations')).toBeDefined();
    
    // Check for tripartite section headers
    expect(screen.getByText('Mission Logs')).toBeDefined();
    expect(screen.getByText('Strategic Dialogue')).toBeDefined();
    expect(screen.getByText('Tool Action Ledger')).toBeDefined();
  });

  it('fetches and displays tripartite feeds when a graph is selected', async () => {
    const mockActions = { actions: [{ id: 1, timestamp: new Date().toISOString(), agent_name: 'Alfredo', action_type: 'web_search', action_details: {}, approval_status: 'APPROVED', cost_usd: 0, duration_seconds: 5, completed_at: new Date().toISOString() }], total: 1 };
    const mockTasks = { tasks: [{ id: 1, title: 'Check market', task_payload: '...', status: 'completed', priority: 'medium', created_at: new Date().toISOString() }], total: 1 };
    const mockConversations = { conversations: [{ id: 1, conversation_key: 'discovery', updated_at: new Date().toISOString(), latest_message: 'Found trends', latest_agent: 'Alfredo' }], total: 1 };

    // Override fetch for this test
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url.includes('/actions')) return Promise.resolve({ ok: true, json: async () => mockActions });
      if (url.includes('/conversations')) return Promise.resolve({ ok: true, json: async () => mockConversations });
      return Promise.resolve({ ok: true, json: async () => mockTasks });
    }));

    render(<Operations graphs={mockGraphs} selectedGraph={mockGraphs[0]} setSelectedGraph={vi.fn()} initialTasks={[]} />);
    
    expect(screen.getByText(`Operations: ${mockGraphs[0].name}`)).toBeDefined();
    
    // Wait for all 3 sections to load data
    await waitFor(() => {
      // Check for raw IDs (1) instead of prefixed strings (T-1, C-1, A-1)
      const idElements = screen.getAllByText(/1/i);
      expect(idElements.length).toBeGreaterThanOrEqual(3); 
    });
    
    expect(screen.getByText('Check market')).toBeDefined();
    expect(screen.getByText('discovery')).toBeDefined();
    expect(screen.getByText(/web_search/i)).toBeDefined();
  });
});

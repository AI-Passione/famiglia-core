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
      return Promise.resolve({
        ok: true,
        json: async () => ({ tasks: [], total: 0 }),
      });
    }));
  });

  it('renders correctly with no selected graph', () => {
    render(<Operations graphs={mockGraphs} selectedGraph={null} setSelectedGraph={vi.fn()} initialTasks={[]} />);
    expect(screen.getByText('Operational History')).toBeDefined();
    // Use getAllByText for messages that might appear in multiple empty feeds
    expect(screen.getAllByText(/Awaiting/)[0]).toBeDefined();
  });

  it('fetches and displays tool actions when a graph is selected', async () => {
    const mockActions = {
      actions: [
        { 
          id: 1, 
          timestamp: new Date().toISOString(), 
          agent_name: 'Alfredo', 
          action_type: 'web_search', 
          action_details: { query: 'test' },
          approval_status: 'APPROVED',
          cost_usd: 0,
          duration_seconds: 5,
          completed_at: new Date().toISOString()
        }
      ],
      total: 1
    };
    
    // Override the global fetch for this specific test
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url.includes('/actions')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockActions,
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ tasks: [], total: 0 }),
      });
    }));

    render(<Operations graphs={mockGraphs} selectedGraph={mockGraphs[0]} setSelectedGraph={vi.fn()} initialTasks={[]} />);
    
    expect(screen.getByText(`Operations: ${mockGraphs[0].name}`)).toBeDefined();
    
    // Wait for the action ID 'A-1' to appear
    const actionIdElement = await screen.findByText(/A-1/i);
    expect(actionIdElement).toBeDefined();
    
    // Check for action type
    expect(screen.getByText(/web_search/i)).toBeDefined();
    
    // Use getAllByText for 'Alfredo' as it appears in the dropdown AND the table row
    const alfredoElements = screen.getAllByText(/Alfredo/i);
    expect(alfredoElements.length).toBeGreaterThanOrEqual(1);
  });
});

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
  });

  it('renders correctly with no selected graph', () => {
    render(<Operations graphs={mockGraphs} selectedGraph={null} setSelectedGraph={vi.fn()} initialTasks={[]} />);
    expect(screen.getByText('Operational History')).toBeDefined();
    expect(screen.getByText('Awaiting neural task signals...')).toBeDefined();
  });

  it('fetches and displays mission logs when a graph is selected', async () => {
    const mockLogs = [
      { id: '1', graph_id: 'market_research', timestamp: '2026-04-01 10:00', status: 'success', duration: '12s', initiator: 'Alfredo' }
    ];
    
    global.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/mission-logs')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockLogs,
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ tasks: [], total: 0 }),
      });
    });

    render(<Operations graphs={mockGraphs} selectedGraph={mockGraphs[0]} setSelectedGraph={vi.fn()} initialTasks={[]} />);
    
    expect(screen.getByText(`Operations: ${mockGraphs[0].name}`)).toBeDefined();
    
    await waitFor(() => {
      expect(screen.getByText('1')).toBeDefined();
      expect(screen.getByText('success')).toBeDefined();
      expect(screen.getByText('Alfredo')).toBeDefined();
    });
  });
});

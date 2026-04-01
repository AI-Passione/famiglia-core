import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SOP } from '@/modules/SOP';
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

describe('SOP Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders correctly with no selected graph', () => {
    render(<SOP graphs={mockGraphs} selectedGraph={null} setSelectedGraph={vi.fn()} />);
    expect(screen.getByText('SOP: Standard Operation Procedure')).toBeDefined();
    expect(screen.getByText('Awaiting connection to deep archives...')).toBeDefined();
  });

  it('fetches and displays mission logs when a graph is selected', async () => {
    const mockLogs = [
      { id: '1', timestamp: '2026-04-01 10:00', status: 'success', duration: '12s', initiator: 'Alfredo' }
    ];
    
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockLogs,
    });

    render(<SOP graphs={mockGraphs} selectedGraph={mockGraphs[0]} setSelectedGraph={vi.fn()} />);
    
    expect(screen.getByText(`SOP: ${mockGraphs[0].name}`)).toBeDefined();
    
    await waitFor(() => {
      expect(screen.getByText('1')).toBeDefined();
      expect(screen.getByText('success')).toBeDefined();
      expect(screen.getByText('Alfredo')).toBeDefined();
    });
  });
});

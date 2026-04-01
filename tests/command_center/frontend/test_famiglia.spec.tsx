import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';

import { Famiglia } from '@/modules/Famiglia';

describe('Famiglia Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders PostgreSQL-backed agent roster cards', async () => {
    (global as any).fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: 'alfredo',
          agent_id: 'alfredo',
          name: 'Alfredo',
          role: 'Strategic Lead',
          status: 'active',
          aliases: ['Chief of Staff'],
          personality: 'Calm and precise',
          identity: 'Coordinates the family.',
          skills: ['Coordination'],
          tools: ['github'],
          workflows: ['Command Center'],
          latest_conversation_snippet: 'Status confirmed.',
          last_active: '2026-03-31T17:00:00Z',
        },
      ],
    });

    render(<Famiglia />);

    await waitFor(() => {
      expect(screen.getByText('Alfredo')).toBeTruthy();
      expect(screen.getByText('Strategic Lead')).toBeTruthy();
      expect(screen.getByText('Agent ID:')).toBeTruthy();
      expect(screen.getByText('Chief of Staff')).toBeTruthy();
      expect(screen.getByText('Coordinates the family.')).toBeTruthy();
      expect(screen.getByText('Command Center')).toBeTruthy();
      expect(screen.getByText('1 Active Agents')).toBeTruthy();
      expect(screen.getByText('1 Total Souls')).toBeTruthy();
      expect(screen.getByText(/Status confirmed\./i)).toBeTruthy();
    });
  });

  it('renders empty state when no agent rows exist', async () => {
    (global as any).fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });

    render(<Famiglia />);

    await waitFor(() => {
      expect(screen.getByText('No agents found')).toBeTruthy();
    });
  });

  it('renders the PostgreSQL error state when roster fetch fails', async () => {
    (global as any).fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({}),
    });

    render(<Famiglia />);

    await waitFor(() => {
      expect(screen.getByText('The Famiglia')).toBeTruthy();
      expect(screen.getByText('Unable to load The Famiglia roster from PostgreSQL.')).toBeTruthy();
    });
  });
});

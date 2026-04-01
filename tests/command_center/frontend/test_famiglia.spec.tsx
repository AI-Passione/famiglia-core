import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';

import { Famiglia } from '@/modules/Famiglia';

vi.mock('@/modules/AgentEditModal', () => ({
  AgentEditModal: ({ agent, onClose }: { agent: any, onClose: () => void }) => (
    <div data-testid="mock-modal">
      EDIT {agent.name.toUpperCase()}
      <button onClick={onClose}>Close</button>
    </div>
  ),
}));

describe('Famiglia Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockAgent = {
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
  };

  it('renders PostgreSQL-backed agent roster cards', async () => {
    (global as any).fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/capabilities')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ tools: [], skills: [], workflows: [] }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => [mockAgent],
      });
    });

    render(<Famiglia />);

    await waitFor(() => {
      expect(screen.getByText('Alfredo')).toBeTruthy();
      expect(screen.getByText('Strategic Lead')).toBeTruthy();
      expect(screen.getByText(/Coordinates the family\./i)).toBeTruthy();
      expect(screen.getByText('Command Center')).toBeTruthy();
    });

    // Test clicking the Edit button
    const editButton = screen.getByTitle('Edit Agent Dossier');
    fireEvent.click(editButton);
    
    await waitFor(() => {
      expect(screen.getByTestId('mock-modal')).toBeTruthy();
      expect(screen.getByTestId('mock-modal').textContent).toContain('EDIT');
      expect(screen.getByTestId('mock-modal').textContent).toContain('ALFREDO');
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

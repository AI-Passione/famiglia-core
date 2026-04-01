import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import React from 'react';

import { Lounge } from '@/modules/Lounge';

describe('Lounge Component', () => {
  it('renders the lounge layout for active agents', () => {
    render(
      <Lounge
        agents={[
          {
            name: 'Alfredo',
            last_active: '2026-04-01T18:15:00Z',
            msg_count: 22,
            status: 'thinking',
          },
          {
            name: 'Bella',
            last_active: '2026-04-01T18:07:00Z',
            msg_count: 15,
            status: 'idle',
          },
        ]}
        actions={[
          {
            id: 7,
            timestamp: '2026-04-01T18:14:00Z',
            agent_name: 'Alfredo',
            action_type: 'market_scan',
            action_details: null,
            approval_status: 'approved',
            duration_seconds: 18,
            completed_at: '2026-04-01T18:14:20Z',
          },
        ]}
      />
    );

    expect(screen.getByTestId('lounge-page')).toBeTruthy();
    expect(screen.getByText('The Poker Table')).toBeTruthy();
    expect(screen.getByText('Digital Resonance')).toBeTruthy();
    expect(screen.getByText('In Attendance')).toBeTruthy();
    expect(screen.getAllByText('Alfredo').length).toBeGreaterThan(0);
    expect(screen.getByText('Inject Thought')).toBeTruthy();
  });

  it('injects a visible Don Jimmy thought into the feed', () => {
    render(
      <Lounge
        agents={[
          {
            name: 'Alfredo',
            last_active: '2026-04-01T18:15:00Z',
            msg_count: 22,
            status: 'thinking',
          },
        ]}
        actions={[]}
      />
    );

    fireEvent.click(screen.getByText('Inject Thought'));

    expect(
      screen.getByText(/Don Jimmy let a small question drift over the felt/i)
    ).toBeTruthy();
    expect(screen.getByText(/answered from the rail/i)).toBeTruthy();
  });

  it('shows the quiet-state message when no agents are present', () => {
    render(<Lounge agents={[]} actions={[]} />);

    expect(screen.getAllByText('No one is in the lounge yet.').length).toBeGreaterThan(0);
  });
});

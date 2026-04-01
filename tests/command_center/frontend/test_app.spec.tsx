import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '@/App';
import React from 'react';

// Mock child components to avoid deep testing
vi.mock('@/modules/SituationRoom', () => ({
  SituationRoom: () => <div data-testid="situation-room">Situation Room</div>
}));
vi.mock('@/modules/SOP', () => ({
  SOP: () => <div data-testid="sop-page">SOP Page</div>
}));
vi.mock('@/modules/Connections', () => ({
  Connections: () => <div data-testid="connections-page">Connections Page</div>
}));

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.removeItem('command_center_settings');
    // Default fetch mocks
    global.fetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (url.includes('/agents')) return Promise.resolve({ ok: true, json: async () => [] });
      if (url.includes('/actions')) return Promise.resolve({ ok: true, json: async () => [] });
      if (url.includes('/tasks')) return Promise.resolve({ ok: true, json: async () => [] });
      if (url.includes('/graphs')) return Promise.resolve({ ok: true, json: async () => [] });
      if (url.includes('/settings')) {
        if (options?.method === 'PUT') {
          return Promise.resolve({
            ok: true,
            json: async () => JSON.parse((options.body as string) || '{}'),
          });
        }

        const existing = window.localStorage.getItem('command_center_settings');
        return Promise.resolve({
          ok: true,
          json: async () =>
            existing
              ? JSON.parse(existing)
              : {
                  honorific: 'Don',
                  notificationsEnabled: true,
                  backgroundAnimationsEnabled: true,
                },
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
  });

  it('renders Situation Room by default', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId('situation-room')).toBeDefined();
    });
  });

  it('switches tabs correctly', async () => {
    render(<App />);
    
    // Find the SOP link in the Sidebar (assuming Sidebar uses these names)
    // Actually Sidebar has "SOP" text
    const sopLink = screen.getByText('SOP');
    fireEvent.click(sopLink);
    
    await waitFor(() => {
      expect(screen.getByTestId('sop-page')).toBeDefined();
    });

    const connectionsLink = screen.getByText('Connections');
    fireEvent.click(connectionsLink);
    
    await waitFor(() => {
      expect(screen.getByTestId('connections-page')).toBeDefined();
    });

    const settingsLink = screen.getByText('Settings');
    fireEvent.click(settingsLink);
    await waitFor(() => {
      expect(screen.getByText(/Configure how the Command Center addresses you/i)).toBeDefined();
    });
  });

  it('fetches initial data on mount', async () => {
    render(<App />);
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/agents'));
      expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('/graphs'));
    });
  });

  it('loads settings from localStorage and persists updates', async () => {
    window.localStorage.setItem(
      'command_center_settings',
      JSON.stringify({
        honorific: 'Donna',
        notificationsEnabled: false,
        backgroundAnimationsEnabled: true,
      })
    );

    render(<App />);
    fireEvent.click(screen.getByText('Settings'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Custom honorific')).toHaveValue('Donna');
    });

    const honorificInput = screen.getByPlaceholderText('Custom honorific');
    fireEvent.change(honorificInput, { target: { value: 'Boss' } });

    await waitFor(() => {
      expect(JSON.parse(window.localStorage.getItem('command_center_settings') || '{}').honorific).toBe('Boss');
    });
  });
});

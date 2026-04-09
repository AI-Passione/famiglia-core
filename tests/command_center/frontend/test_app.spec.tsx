import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import App from '@/App';
import React from 'react';

// Mock child components to avoid deep testing
vi.mock('@/modules/Agenda', () => ({
  Agenda: () => <div data-testid="agenda-page">Agenda Page</div>
}));
vi.mock('@/modules/SituationRoom', () => ({
  SituationRoom: () => <div data-testid="situation-room">Situation Room</div>
}));
vi.mock('@/modules/EngineRoom', () => ({
  EngineRoom: () => <div data-testid="engine-room-page">Engine Room</div>
}));
vi.mock('@/modules/Operations', () => ({
  Operations: () => <div data-testid="operations-page">Operations Page</div>
}));
vi.mock('@/modules/Connections', () => ({
  Connections: () => <div data-testid="connections-page">Connections Page</div>
}));
vi.mock('@/modules/Famiglia', () => ({
  Famiglia: () => <div data-testid="famiglia-page">Famiglia Page</div>
}));
vi.mock('@/modules/Lounge', () => ({
  Lounge: () => <div data-testid="lounge-page">Lounge Page</div>
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
      if (url.includes('/recurring-tasks')) return Promise.resolve({ ok: true, json: async () => [] });
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

  it('renders The Situation Room by default', async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByTestId('situation-room')).toBeDefined();
    });
  });

  it('switches tabs correctly', async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );

    const agendaLink = screen.getByText('The Agenda');
    fireEvent.click(agendaLink);

    await waitFor(() => {
      expect(screen.getByTestId('agenda-page')).toBeDefined();
    });

    const situationRoomLink = screen.getByText('The Situation Room');
    fireEvent.click(situationRoomLink);

    await waitFor(() => {
      expect(screen.getByTestId('situation-room')).toBeDefined();
    });

    const settingsLink = screen.getByText('Settings');
    fireEvent.click(settingsLink);
    await waitFor(() => {
      expect(screen.getByText(/Command Center Configuration & Telemetry/i)).toBeDefined();
    });

    const famigliaLink = screen.getByText('The Famiglia');
    fireEvent.click(famigliaLink);
    await waitFor(() => {
      expect(screen.getByTestId('famiglia-page')).toBeDefined();
    });
  });

  it('fetches initial data on mount', async () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );
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
        personalDirective: '',
        systemPrompt: '',
      })
    );

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );
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

  it('hydrates settings from backend and syncs updates with PUT', async () => {
    global.fetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (url.includes('/agents')) return Promise.resolve({ ok: true, json: async () => [] });
      if (url.includes('/actions')) return Promise.resolve({ ok: true, json: async () => [] });
      if (url.includes('/tasks')) return Promise.resolve({ ok: true, json: async () => [] });
      if (url.includes('/recurring-tasks')) return Promise.resolve({ ok: true, json: async () => [] });
      if (url.includes('/graphs')) return Promise.resolve({ ok: true, json: async () => [] });
      if (url.includes('/settings')) {
        if (options?.method === 'PUT') {
          return Promise.resolve({ ok: true, json: async () => ({}) });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({
            honorific: 'Capo',
            notificationsEnabled: true,
            backgroundAnimationsEnabled: false,
            personalDirective: '',
            systemPrompt: '',
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );
    fireEvent.click(screen.getByText('Settings'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Custom honorific')).toHaveValue('Capo');
    });

    fireEvent.change(screen.getByPlaceholderText('Custom honorific'), {
      target: { value: 'Donna' },
    });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/settings'),
        expect.objectContaining({ method: 'PUT' })
      );
    });
  });

  it('handles backend 404s and malformed data gracefully without corrupting the render tree', async () => {
    // Override fetch mock perfectly for this exact crash scenario
    global.fetch = vi.fn().mockImplementation((url: string) => {
      // Simulate 404 Not Found object returns for all data streams
      return Promise.resolve({ 
        ok: false, 
        json: async () => ({ detail: "Not Found" }) 
      });
    });

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );

    // If it handled it safely, the Situation Room structure still renders without crashing.
    // The "Actionable Directives" header comes from OperationsHub.
    await waitFor(() => {
      expect(screen.getByText('Actionable Directives')).toBeDefined();
    });
    
    // There should be a "No pending directives" or "Awaiting Intel..." message since it's empty
    expect(screen.getByText('No pending directives')).toBeDefined();
    expect(screen.getByText('Awaiting Intel...')).toBeDefined();
  });
});

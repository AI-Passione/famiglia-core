import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Connections } from '@/modules/Connections';
import React from 'react';

describe('Connections Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    (global as any).fetch = vi.fn().mockImplementation(() => new Promise(() => {}));
    render(<Connections />);
    // In our theme, the loading icon name is nest_remote_comfort_sensor
    expect(screen.getByText('nest_remote_comfort_sensor')).toBeTruthy();
  });

  it('renders service cards after data is fetched', async () => {
    const mockConfig = {
      github: { configured: true, redirect_uri: 'http://localhost' },
      slack: { configured: true, redirect_uri: 'http://localhost' }
    };
    const mockStatus = { connected: false };

    (global as any).fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/connections/config')) return Promise.resolve({ ok: true, json: async () => mockConfig });
      return Promise.resolve({ ok: true, json: async () => mockStatus });
    });

    render(<Connections />);

    await waitFor(() => {
      expect(screen.getByText('GitHub Account')).toBeTruthy();
      expect(screen.getByText('Slack Famiglia')).toBeTruthy();
      expect(screen.getByText('Notion Workspace')).toBeTruthy();
    });
  });

  it('shows toast message when successParam is true', async () => {
    const mockConfig = {};
    const mockStatus = { connected: false };

    (global as any).fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/connections/config')) return Promise.resolve({ ok: true, json: async () => mockConfig });
        return Promise.resolve({ ok: true, json: async () => mockStatus });
      });

    render(<Connections successParam="true" />);

    await waitFor(() => {
      expect(screen.getByText('Successfully linked service account.')).toBeTruthy();
    });
  });
});

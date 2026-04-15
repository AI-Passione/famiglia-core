import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Connections } from '@/modules/Connections';
import React from 'react';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const BASE_CONFIG = {
  github: { configured: false, redirect_uri: 'http://localhost' },
  slack: { configured: false, redirect_uri: 'http://localhost' },
  notion: { configured: false, redirect_uri: 'http://localhost' },
};

function buildFetch({
  config = BASE_CONFIG,
  ollamaStatus = { connected: false },
  saveOllamaResponse = { ok: true, body: { success: true } },
  testOllamaResponse = { ok: true, body: { success: true, host: 'http://127.0.0.1:11434', models: ['gemma3:4b'] } },
  deleteOllamaResponse = { ok: true, body: { success: true } },
}: {
  config?: object;
  ollamaStatus?: object;
  saveOllamaResponse?: { ok: boolean; body: object };
  testOllamaResponse?: { ok: boolean; body: object };
  deleteOllamaResponse?: { ok: boolean; body: object };
} = {}) {
  return vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
    if (url.includes('/connections/config')) {
      return Promise.resolve({ ok: true, json: async () => config });
    }
    if (url.includes('/connections/ollama/key') && opts?.method === 'POST') {
      return Promise.resolve({ ok: saveOllamaResponse.ok, json: async () => saveOllamaResponse.body });
    }
    if (url.includes('/connections/ollama/test')) {
      return Promise.resolve({ ok: testOllamaResponse.ok, json: async () => testOllamaResponse.body });
    }
    if (url.includes('/connections/ollama') && opts?.method === 'DELETE') {
      return Promise.resolve({ ok: deleteOllamaResponse.ok, json: async () => deleteOllamaResponse.body });
    }
    // Catch-all for individual service status endpoints
    if (url.includes('/connections/ollama')) {
      return Promise.resolve({ ok: true, json: async () => ollamaStatus });
    }
    return Promise.resolve({ ok: true, json: async () => ({ connected: false }) });
  });
}

// ─── Disconnected state ───────────────────────────────────────────────────────

describe('OllamaCard — disconnected', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders Ollama card with API key input when disconnected', async () => {
    (global as any).fetch = buildFetch({ ollamaStatus: { connected: false } });
    render(<Connections />);

    await waitFor(() => {
      expect(screen.getByText('Ollama')).toBeTruthy();
    });
    // The placeholder is the masked key pattern used in the component
    expect(screen.getByPlaceholderText('sk-••••••••••••••••')).toBeTruthy();
  });

  it('shows "Save key" button when disconnected', async () => {
    (global as any).fetch = buildFetch({ ollamaStatus: { connected: false } });
    render(<Connections />);

    await waitFor(() => {
      expect(screen.getByText(/save key/i)).toBeTruthy();
    });
  });

  it('saves API key and calls POST endpoint', async () => {
    const mockFetch = buildFetch({ ollamaStatus: { connected: false } });
    (global as any).fetch = mockFetch;
    render(<Connections />);

    await waitFor(() => screen.getByPlaceholderText('sk-••••••••••••••••'));

    const input = screen.getByPlaceholderText('sk-••••••••••••••••');
    fireEvent.change(input, { target: { value: 'sk-my-ollama-key' } });

    // "Save key" button becomes enabled once input has a value
    const saveBtn = screen.getByText(/save key/i).closest('button')!;
    await act(async () => {
      fireEvent.click(saveBtn);
    });

    const postCall = mockFetch.mock.calls.find(
      ([url, opts]: [string, RequestInit]) =>
        url.includes('/connections/ollama/key') && opts?.method === 'POST'
    );
    expect(postCall).toBeTruthy();
    expect(JSON.parse(postCall[1].body)).toMatchObject({ api_key: 'sk-my-ollama-key' });
  });

  it('shows error message when save fails', async () => {
    (global as any).fetch = buildFetch({
      ollamaStatus: { connected: false },
      saveOllamaResponse: { ok: false, body: { detail: 'Failed to save API key.' } },
    });
    render(<Connections />);

    await waitFor(() => screen.getByPlaceholderText('sk-••••••••••••••••'));
    fireEvent.change(screen.getByPlaceholderText('sk-••••••••••••••••'), { target: { value: 'bad-key' } });

    const saveBtn = screen.getByText(/save key/i).closest('button')!;
    await act(async () => {
      fireEvent.click(saveBtn);
    });

    await waitFor(() => {
      expect(screen.getByText('Failed to save API key.')).toBeTruthy();
    });
  });

  it('shows/hides the API key via the visibility toggle', async () => {
    (global as any).fetch = buildFetch({ ollamaStatus: { connected: false } });
    render(<Connections />);

    await waitFor(() => screen.getByPlaceholderText('sk-••••••••••••••••'));
    const input = screen.getByPlaceholderText('sk-••••••••••••••••') as HTMLInputElement;
    expect(input.type).toBe('password');

    // The toggle button contains the Material Symbols icon text "visibility"
    const toggleBtn = screen.getAllByRole('button').find(
      (b) => b.textContent?.trim() === 'visibility' || b.textContent?.trim() === 'visibility_off'
    )!;
    expect(toggleBtn).toBeTruthy();
    fireEvent.click(toggleBtn);
    expect(input.type).toBe('text');
  });
});

// ─── Connected state ──────────────────────────────────────────────────────────

describe('OllamaCard — connected', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders "API Key stored" when connected', async () => {
    (global as any).fetch = buildFetch({
      ollamaStatus: { connected: true, connected_at: '2026-04-15T10:00:00+00:00' },
    });
    render(<Connections />);

    await waitFor(() => {
      expect(screen.getByText('API Key stored')).toBeTruthy();
    });
  });

  it('renders "Test connection" and "Remove key" buttons when connected', async () => {
    (global as any).fetch = buildFetch({
      ollamaStatus: { connected: true, connected_at: '2026-04-15T10:00:00+00:00' },
    });
    render(<Connections />);

    await waitFor(() => {
      expect(screen.getByText(/test connection/i)).toBeTruthy();
      expect(screen.getByText(/remove key/i)).toBeTruthy();
    });
  });

  it('does not render API key input when connected', async () => {
    (global as any).fetch = buildFetch({
      ollamaStatus: { connected: true },
    });
    render(<Connections />);

    await waitFor(() => screen.getByText('API Key stored'));
    expect(screen.queryByPlaceholderText(/api key/i)).toBeNull();
  });
});

// ─── Test connection ──────────────────────────────────────────────────────────

describe('OllamaCard — test connection', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows success panel with host and models on successful test', async () => {
    (global as any).fetch = buildFetch({
      ollamaStatus: { connected: true },
      testOllamaResponse: {
        ok: true,
        body: { success: true, host: 'http://127.0.0.1:11434', models: ['gemma3:4b', 'llama3:latest'] },
      },
    });
    render(<Connections />);

    await waitFor(() => screen.getByText(/test connection/i));

    await act(async () => {
      fireEvent.click(screen.getByText(/test connection/i));
    });

    await waitFor(() => {
      expect(screen.getByText(/gemma3:4b/)).toBeTruthy();
      expect(screen.getByText(/llama3:latest/)).toBeTruthy();
    });
  });

  it('shows error detail on failed test', async () => {
    (global as any).fetch = buildFetch({
      ollamaStatus: { connected: true },
      testOllamaResponse: {
        ok: false,
        body: { detail: 'Could not reach Ollama at http://127.0.0.1:11434. Is it running?' },
      },
    });
    render(<Connections />);

    await waitFor(() => screen.getByText(/test connection/i));

    await act(async () => {
      fireEvent.click(screen.getByText(/test connection/i));
    });

    await waitFor(() => {
      expect(screen.getByText(/Could not reach Ollama/)).toBeTruthy();
    });
  });

  it('calls DELETE endpoint when "Remove key" is clicked', async () => {
    const mockFetch = buildFetch({ ollamaStatus: { connected: true } });
    (global as any).fetch = mockFetch;
    render(<Connections />);

    await waitFor(() => screen.getByText(/remove key/i));

    await act(async () => {
      fireEvent.click(screen.getByText(/remove key/i));
    });

    await waitFor(() => {
      const deleteCall = mockFetch.mock.calls.find(
        ([url, opts]: [string, RequestInit]) =>
          url.includes('/connections/ollama') && opts?.method === 'DELETE'
      );
      expect(deleteCall).toBeTruthy();
    });
  });
});

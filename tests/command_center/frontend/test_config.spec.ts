import { afterEach, describe, expect, it, vi } from 'vitest';

describe('Frontend Config', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('uses the local backend defaults when no env vars are set', async () => {
    vi.resetModules();
    const { BACKEND_BASE, API_BASE } = await import('@/config');

    expect(BACKEND_BASE).toBe('http://localhost:8000');
    expect(API_BASE).toBe('http://localhost:8000/api/v1');
  });

  it('builds API_BASE from a custom backend base', async () => {
    vi.stubEnv('VITE_BACKEND_BASE', 'https://api.aipassione.com/');
    vi.resetModules();

    const { BACKEND_BASE, API_BASE } = await import('@/config');

    expect(BACKEND_BASE).toBe('https://api.aipassione.com');
    expect(API_BASE).toBe('https://api.aipassione.com/api/v1');
  });

  it('prefers an explicit API base when provided', async () => {
    vi.stubEnv('VITE_BACKEND_BASE', 'https://api.aipassione.com/');
    vi.stubEnv('VITE_API_BASE', 'https://api.aipassione.com/api/v1/');
    vi.resetModules();

    const { BACKEND_BASE, API_BASE } = await import('@/config');

    expect(BACKEND_BASE).toBe('https://api.aipassione.com');
    expect(API_BASE).toBe('https://api.aipassione.com/api/v1');
  });
});

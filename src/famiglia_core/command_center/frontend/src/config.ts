const DEFAULT_BACKEND_BASE = 'http://localhost:8000';

function normalizeUrl(value: string): string {
  return value.trim().replace(/\/+$/, '');
}

const rawApiBase = import.meta.env.VITE_API_BASE;
const rawBackendBase = import.meta.env.VITE_BACKEND_BASE;

export const BACKEND_BASE = normalizeUrl(rawBackendBase || DEFAULT_BACKEND_BASE);
export const API_BASE = rawApiBase
  ? normalizeUrl(rawApiBase)
  : `${BACKEND_BASE}/api/v1`;

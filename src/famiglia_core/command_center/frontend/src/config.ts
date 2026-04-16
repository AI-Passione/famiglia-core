const DEFAULT_BACKEND_BASE = '';

function normalizeUrl(value: string): string {
  return value.trim().replace(/\/+$/, '');
}

const rawApiBase = import.meta.env.VITE_API_BASE;
const rawBackendBase = import.meta.env.VITE_BACKEND_BASE;

export const BACKEND_BASE = normalizeUrl(rawBackendBase || DEFAULT_BACKEND_BASE);

// If BACKEND_BASE is just 'http://localhost' or 'https://localhost' without a port, 
// it's likely a misconfiguration for local dev. We should default to relative paths 
// so the Vite proxy can handle it.
const isInvalidLocalhost = /^https?:\/\/localhost\/?$/.test(BACKEND_BASE);

export const API_BASE = rawApiBase
  ? normalizeUrl(rawApiBase)
  : (BACKEND_BASE && !isInvalidLocalhost ? `${BACKEND_BASE}/api/v1` : `/api/v1`);

// MISSION CRITICAL: Global Debug Exposure
(window as any).DEBUG_CONFIG = {
  BACKEND_BASE,
  API_BASE,
  ORIGIN: window.location.origin,
  VITE_API: rawApiBase,
  VITE_BACKEND: rawBackendBase
};

console.log("[DEBUG] Config initialized:", (window as any).DEBUG_CONFIG);

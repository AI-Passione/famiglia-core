const DEFAULT_BACKEND_BASE = '';

function normalizeUrl(value: string): string {
  return value.trim().replace(/\/+$/, '');
}

const rawApiBase = import.meta.env.VITE_API_BASE;
const rawBackendBase = import.meta.env.VITE_BACKEND_BASE;

export const BACKEND_BASE = normalizeUrl(rawBackendBase || DEFAULT_BACKEND_BASE);
export const API_BASE = rawApiBase
  ? normalizeUrl(rawApiBase)
  : (BACKEND_BASE ? `${BACKEND_BASE}/api/v1` : `${window.location.origin}/api/v1`);

// MISSION CRITICAL: Global Debug Exposure
(window as any).DEBUG_CONFIG = {
  BACKEND_BASE,
  API_BASE,
  ORIGIN: window.location.origin,
  VITE_API: rawApiBase,
  VITE_BACKEND: rawBackendBase
};

console.log("[DEBUG] Config initialized:", (window as any).DEBUG_CONFIG);

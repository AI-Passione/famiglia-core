import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';

import { EngineRoom } from '@/modules/EngineRoom';

describe('EngineRoom Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the local telemetry snapshot', async () => {
    (global as any).fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        scope: 'local-only',
        generated_at: '2026-04-01T11:30:00Z',
        host: {
          hostname: 'la-passione.local',
          platform: {
            system: 'Darwin',
            release: '24.0.0',
            machine: 'arm64',
            python: '3.12.8',
          },
          uptime: {
            seconds: 86400,
            display: '1d',
            source: 'uptime_command',
          },
          cpu: {
            cores: 10,
            load_average: [1.2, 1.6, 1.9],
            estimated_load_percent: 12,
            source: 'load_average_per_core',
          },
          memory: {
            total_bytes: 17179869184,
            used_bytes: 8589934592,
            available_bytes: 8589934592,
            usage_percent: 50,
            source: 'vm_stat',
          },
          disk: {
            path: '/Users/jimmypang/AIPassioneProjects/famiglia-core',
            total_bytes: 1000,
            used_bytes: 500,
            free_bytes: 500,
            usage_percent: 50,
          },
        },
        tools: {
          summary: {
            total: 8,
            ready: 5,
            connected: 2,
            configured: 6,
          },
          items: [
            {
              slug: 'github',
              name: 'GitHub',
              category: 'Code',
              description: 'Repository, PR, and issue operations.',
              configured: true,
              connected: true,
              status: 'connected',
              detail: 'don-jimmy',
            },
          ],
        },
        docker: {
          available: true,
          compose_file: '/Users/jimmypang/AIPassioneProjects/famiglia-core/docker-compose.yml',
          diagnostics: [],
          summary: {
            declared: 4,
            reachable: 3,
            live: 3,
            healthy: 3,
          },
          services: [
            {
              name: 'app',
              image: null,
              profiles: [],
              ports: [{ host_port: 8000, container_port: 8000, raw: '8000:8000' }],
              has_healthcheck: false,
              reachable: true,
              state: 'running',
              health: 'healthy',
              source: 'docker_compose_ps',
            },
          ],
        },
        observability: {
          summary: {
            total: 4,
            configured: 4,
            reachable: 3,
          },
          metrics: [
            {
              label: 'Tracing',
              value: 'Enabled',
              hint: 'Langfuse host binding for local traces.',
              tone: 'good',
            },
          ],
          items: [
            {
              name: 'Grafana',
              service_name: 'grafana',
              description: 'Dashboard surface for local infrastructure signals.',
              url: 'http://localhost:3000',
              configured: true,
              reachable: true,
              state: 'running',
              health: 'healthy',
            },
          ],
        },
      }),
    });

    render(<EngineRoom />);

    await waitFor(() => {
      expect(screen.getByText('The Engine Room')).toBeTruthy();
      expect(screen.getByText('GitHub')).toBeTruthy();
      expect(screen.getByText('Container and port health')).toBeTruthy();
      expect(screen.getByText('Grafana')).toBeTruthy();
    });
  });
});

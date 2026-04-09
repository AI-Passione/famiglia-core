import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Terminal } from '@/modules/Terminal';
import { TerminalProvider } from '@/modules/TerminalContext';
import { ErrorBoundary } from '@/modules/ui/ErrorBoundary';
import React from 'react';

// --- Mocks ---

// Mock scrollIntoView
if (typeof window !== 'undefined') {
  window.Element.prototype.scrollIntoView = vi.fn();
}

// Mock EventSource
class MockEventSource {
  onmessage: ((event: any) => void) | null = null;
  onerror: ((err: any) => void) | null = null;
  close = vi.fn();
  constructor(public url: string) {}
}
vi.stubGlobal('EventSource', MockEventSource);

// --- Test Suite ---

describe('Terminal Stability & Regression', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  const renderWithBoundary = async (ui: React.ReactElement) => {
    await act(async () => {
      render(
        <ErrorBoundary>
          <TerminalProvider>
            {ui}
          </TerminalProvider>
        </ErrorBoundary>
      );
    });
  };

  describe('Malformed Backend Data Resilience', () => {
    it('handles agents with null or missing IDs without crashing', async () => {
      // Mock fetch to return some malformed agent data
      vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
        if (url.includes('/famiglia/agents')) {
          return Promise.resolve({
            ok: true,
            json: async () => [
              { id: 1, name: 'Agent 1', status: 'active', agent_id: 'alfredo' },
              { id: 2, name: 'Broken Agent', status: null, agent_id: null }, // Missing agent_id
              null, // Null entry in array
              { name: 'Missing ID' } // Completely malformed
            ]
          });
        }
        return Promise.resolve({ ok: true, json: async () => ({ actions: [] }) });
      }));

      await renderWithBoundary(<Terminal variant="full" />);
      
      // Verify first agent is there
      expect(await screen.findByText(/Hierarchy/i)).toBeDefined();
      // Should not show Error Boundary
      expect(screen.queryByText(/Terminal Critical Failure/i)).toBeNull();
    });

    it('handles message history with undefined or null senders safely', async () => {
      vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
        if (url.includes('/chat/history')) {
          return Promise.resolve({
            ok: true,
            json: async () => [
              { id: 1, sender: 'Alfredo', role: 'Agent', content: 'Good message', created_at: new Date().toISOString() },
              { id: 2, sender: null, role: null, content: 'Bad sender', created_at: new Date().toISOString() }, // Null sender
              { id: 3, content: 'Missing sender', created_at: new Date().toISOString() } // Missing sender
            ]
          });
        }
        return Promise.resolve({ ok: true, json: async () => [] });
      }));

      await renderWithBoundary(<Terminal variant="full" />);
      
      // Should handle messages without crashing
      expect(await screen.findByText('Good message')).toBeDefined();
      expect(screen.getByText('Bad sender')).toBeDefined();
      expect(screen.getByText('Missing sender')).toBeDefined();
      expect(screen.queryByText(/Terminal Critical Failure/i)).toBeNull();
    });

    it('handles rapid channel switching with potentially missing state', async () => {
      await renderWithBoundary(<Terminal variant="full" />);
      
      // Switch to Lounge
      const loungeBtn = screen.getByText(/lounge/i).closest('button');
      await act(async () => {
        fireEvent.click(loungeBtn!);
      });

      // Rapidly switch back and forth
      const commandBtn = screen.getByText(/command-center/i).closest('button');
      await act(async () => {
        fireEvent.click(commandBtn!);
        fireEvent.click(loungeBtn!);
        fireEvent.click(commandBtn!);
      });

      expect(screen.queryByText(/Terminal Critical Failure/i)).toBeNull();
    });
  });

  describe('ErrorBoundary Functionality', () => {
    it('catches and displays catastrophic runtime errors', async () => {
      // Create a component that definitely crashes
      const ExplodingComponent = () => {
        throw new Error('KABOOM');
      };

      // Silence console error for this test to avoid polluting logs
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      await act(async () => {
        render(
          <ErrorBoundary>
            <ExplodingComponent />
          </ErrorBoundary>
        );
      });

      // Should show the recovery UI instead of a blank screen
      expect(screen.getByText(/Terminal Critical Failure/i)).toBeDefined();
      expect(screen.getAllByText(/KABOOM/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/Clear Local Intelligence & Reboot/i)).toBeDefined();

      consoleSpy.mockRestore();
    });
  });
});

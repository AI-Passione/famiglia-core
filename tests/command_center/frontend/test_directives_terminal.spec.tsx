import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DirectivesTerminal } from '@/modules/ui/DirectivesTerminal';
import { TerminalProvider } from '@/modules/TerminalContext';
import React from 'react';

// Mock EventSource
class MockEventSource {
  onmessage: ((event: any) => void) | null = null;
  onerror: ((err: any) => void) | null = null;
  close = vi.fn();
  url: string;
  constructor(url: string) {
    this.url = url;
  }
}

vi.stubGlobal('EventSource', MockEventSource);

// Mock scrollIntoView as it's not implemented in JSDOM
if (typeof window !== 'undefined') {
  window.Element.prototype.scrollIntoView = vi.fn();
}

// Mock fetch for the TerminalProvider's internal data fetching
vi.stubGlobal('fetch', vi.fn().mockImplementation(() => Promise.resolve({
  ok: true,
  json: async () => ({ agents: [], actions: [] })
})));

describe('DirectivesTerminal Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithProvider = async (ui: React.ReactElement) => {
    await act(async () => {
      render(
        <TerminalProvider>
          {ui}
        </TerminalProvider>
      );
    });
  };

  it('renders the floating action button initially', async () => {
    await renderWithProvider(<DirectivesTerminal />);
    expect(screen.getByText('Directives Terminal')).toBeDefined();
  });

  it('opens the terminal window when the FAB is clicked', async () => {
    await renderWithProvider(<DirectivesTerminal />);
    const button = screen.getByText('Directives Terminal').closest('button');
    
    await act(async () => {
      fireEvent.click(button!);
    });
    
    // Use findBy to wait for the terminal content to appear
    const message = await screen.findByText(/#command-center is secure/i);
    expect(message).toBeDefined();
  });

  it('closes the terminal when the close button is clicked', async () => {
    await renderWithProvider(<DirectivesTerminal />);
    const fab = screen.getByText('Directives Terminal').closest('button');
    
    await act(async () => {
      fireEvent.click(fab!);
    });
    
    await screen.findByText(/#command-center is secure/i);

    const closeButton = (await screen.findAllByRole('button', { name: /close/i }))[0];
    await act(async () => {
      fireEvent.click(closeButton!);
    });

    await waitFor(() => {
      expect(screen.queryByText(/#command-center is secure/i)).toBeNull();
    });
  });

  it('updates input value on change', async () => {
    await renderWithProvider(<DirectivesTerminal />);
    await act(async () => {
      fireEvent.click(screen.getByText('Directives Terminal').closest('button')!);
    });
    
    const textarea = await screen.findByPlaceholderText(/Compose directive for/i);
    await act(async () => {
      fireEvent.change(textarea, { target: { value: 'Hello Alfredo' } });
    });
    expect((textarea as HTMLTextAreaElement).value).toBe('Hello Alfredo');
  });
});

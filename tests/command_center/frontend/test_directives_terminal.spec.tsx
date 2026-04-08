import { render, screen, fireEvent, waitFor, act, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DirectivesTerminal } from '@/modules/ui/DirectivesTerminal';
import { Terminal } from '@/modules/Terminal';
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
    localStorage.clear();
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

  describe('Threading', () => {
    it('opens the thread panel when reply is clicked on a message with db_id', async () => {
      // Mock fetch to provide a message with a db_id during rehydration
      vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
        if (url.includes('/chat/history')) {
          return Promise.resolve({
            ok: true,
            json: async () => [{ id: 101, sender: 'Alfredo', role: 'Agent', content: 'Thread starter', created_at: new Date().toISOString() }]
          });
        }
        if (url.includes('/chat/thread')) {
          return Promise.resolve({ ok: true, json: async () => [] });
        }
        return Promise.resolve({ ok: true, json: async () => [] });
      }));

      await renderWithProvider(<Terminal variant="full" />);
      
      // Wait for history to load and message to appear
      await screen.findByText('Thread starter');
      const replyButtons = await screen.findAllByTestId('reply-button');
      
      await act(async () => {
        // Use the second reply button (the first is the welcome message which has no db_id)
        fireEvent.click(replyButtons[1]); 
      });

      // Thread panel should appear
      const threadPanel = await screen.findByTestId('thread-panel');
      expect(within(threadPanel).getByText('Alfredo')).toBeDefined();
    });

    it('closes the thread panel when the close button is clicked', async () => {
       // Setup thread...
       vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
        if (url.includes('/chat/history')) {
          return Promise.resolve({
            ok: true,
            json: async () => [{ id: 101, sender: 'Alfredo', role: 'Agent', content: 'Thread starter', created_at: new Date().toISOString() }]
          });
        }
        if (url.includes('/chat/thread')) {
          return Promise.resolve({ ok: true, json: async () => [] });
        }
        return Promise.resolve({ ok: true, json: async () => [] });
      }));

      await renderWithProvider(<Terminal variant="full" />);

      const replyButtons = await screen.findAllByTestId('reply-button');
      await act(async () => { fireEvent.click(replyButtons[1]); });
      
      await screen.findByTestId('thread-panel');

      const closeThreadButton = screen.getByText('close').closest('button');
      await act(async () => {
        fireEvent.click(closeThreadButton!);
      });

      await waitFor(() => {
        expect(screen.queryByTestId('thread-panel')).toBeNull();
      });
    });
  });

  describe('Scrolling Logic', () => {
    it('triggers scrollToBottom on new user message', async () => {
      const scrollToSpy = vi.fn();
      window.Element.prototype.scrollTo = scrollToSpy;

      await renderWithProvider(<Terminal variant="full" />);

      const textarea = await screen.findByPlaceholderText(/Compose directive for/i);
      await act(async () => {
        fireEvent.change(textarea, { target: { value: 'Scroll test' } });
      });

      const executeButton = screen.getByText('Execute').closest('button');
      await act(async () => {
        fireEvent.click(executeButton!);
      });

      // Should call scrollTo with auto behavior for user message
      expect(scrollToSpy).toHaveBeenCalled();
    });

    it('shows "New Messages" button when scrolled up and a new agent message arrives', async () => {
      await renderWithProvider(<Terminal variant="full" />);

      // Find the scroll container
      const scrollContainer = await screen.findByTestId('terminal-scroll-container');
      
      // Simulate being scrolled up
      // Manually mock the properties since JSDOM doesn't
      Object.defineProperty(scrollContainer, 'scrollHeight', { value: 1000, configurable: true });
      Object.defineProperty(scrollContainer, 'scrollTop', { value: 100, configurable: true });
      Object.defineProperty(scrollContainer, 'clientHeight', { value: 500, configurable: true });

      // Trigger scroll handle to update internal isAtBottom state
      await act(async () => {
        fireEvent.scroll(scrollContainer);
      });

      // Now we need to mock a message arrival. 
      // Instead of relying on sendMessage (which scrolls to bottom), 
      // we'll mock the next messages update behavior.
      const textarea = await screen.findByPlaceholderText(/Compose directive for/i);
      await act(async () => {
        fireEvent.change(textarea, { target: { value: 'Trigger' } });
      });

      // We click execute, which will add a user message (scrolls) then typing indicator.
      // To prevent the scroll from resetting isAtBottom, we'll mock scrollTo to do nothing to scrollTop
      scrollContainer.scrollTo = vi.fn(); 

      const executeButton = screen.getByText('Execute').closest('button');
      await act(async () => {
        fireEvent.click(executeButton!);
      });

      // Wait for "New Messages" button to appear
      // We use findByTestId to be sure
      const newMessagesButton = await screen.findByTestId('new-messages-button');
      expect(newMessagesButton).toBeDefined();

      // Click it and verify it scrolls to bottom
      const scrollToSpy = vi.fn();
      scrollContainer.scrollTo = scrollToSpy;
      await act(async () => {
        fireEvent.click(newMessagesButton);
      });
      expect(scrollToSpy).toHaveBeenCalled();
    });
  });
});

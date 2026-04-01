import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DirectivesTerminal } from '@/modules/ui/DirectivesTerminal';
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

describe('DirectivesTerminal Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the floating action button initially', () => {
    render(<DirectivesTerminal />);
    expect(screen.getByText('Directives Terminal')).toBeDefined();
    expect(screen.queryByText('Agent Alfredo Online')).toBeNull();
  });

  it('opens the terminal window when the FAB is clicked', async () => {
    render(<DirectivesTerminal />);
    const button = screen.getByText('Directives Terminal').closest('button');
    if (!button) throw new Error('Button not found');
    
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(screen.getByText('Agent Alfredo Online')).toBeDefined();
    });
  });

  it('closes the terminal when the close button is clicked', async () => {
    render(<DirectivesTerminal />);
    const fab = screen.getByText('Directives Terminal').closest('button');
    fireEvent.click(fab!);
    
    await waitFor(() => {
      expect(screen.getByText('Agent Alfredo Online')).toBeDefined();
    });

    const closeButton = screen.getAllByRole('button', { name: /close/i })[0];
    fireEvent.click(closeButton!);

    await waitFor(() => {
      expect(screen.queryByText('Agent Alfredo Online')).toBeNull();
    });
  });

  it('updates input value on change', async () => {
    render(<DirectivesTerminal />);
    fireEvent.click(screen.getByText('Directives Terminal').closest('button')!);
    
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Issue a directive...')).toBeDefined();
    });

    const textarea = screen.getByPlaceholderText('Issue a directive...');
    fireEvent.change(textarea, { target: { value: 'Hello Alfredo' } });
    expect((textarea as HTMLTextAreaElement).value).toBe('Hello Alfredo');
  });
});

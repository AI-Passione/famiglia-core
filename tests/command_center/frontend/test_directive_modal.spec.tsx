import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DirectiveModal } from '@/modules/ui/DirectiveModal';
import { ToastProvider, useToast } from '@/modules/ui/ToastProvider';
import React from 'react';
import type { GraphDefinition } from '@/types';

// Mock useToast to verify notifications
vi.mock('@/modules/ui/ToastProvider', async (importOriginal) => {
  const actual = await importOriginal() as any;
  return {
    ...actual,
    useToast: vi.fn(),
  };
});

describe('DirectiveModal Component', () => {
  const mockGraphs: GraphDefinition[] = [
    { id: 'simple_data_analysis', name: 'Simple Data Analysis', category: 'Analytics', nodes: [], edges: [] },
    { id: 'prd_drafting', name: 'PRD Drafting', category: 'Product', nodes: [], edges: [] },
  ];
  const mockShowToast = vi.fn();
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useToast as any).mockReturnValue({ showToast: mockShowToast });
    
    global.fetch = vi.fn().mockImplementation(() => 
      Promise.resolve({
        ok: true,
        json: async () => ({ message: 'Directive dispatched to Kowalski', task_id: 123 })
      })
    );
  });

  it('renders correctly when open', () => {
    render(
      <DirectiveModal isOpen={true} onClose={mockOnClose} graphs={mockGraphs} />
    );
    
    expect(screen.getByText('Execute Directive')).toBeDefined();
    expect(screen.getByText('Simple Data Analysis')).toBeDefined();
    expect(screen.getByPlaceholderText(/Enter custom instructions/i)).toBeDefined();
  });

  it('allows selecting a quick directive', async () => {
    render(
      <DirectiveModal isOpen={true} onClose={mockOnClose} graphs={mockGraphs} />
    );
    
    const directiveBtn = screen.getByText('Simple Data Analysis');
    fireEvent.click(directiveBtn);
    
    // The button should show a checkmark (material icon)
    expect(screen.getByText('check_circle')).toBeDefined();
  });

  it('clears manual prompt when a quick directive is selected', () => {
    render(
      <DirectiveModal isOpen={true} onClose={mockOnClose} graphs={mockGraphs} />
    );
    
    const textarea = screen.getByPlaceholderText(/Enter custom instructions/i) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'Manual task' } });
    expect(textarea.value).toBe('Manual task');
    
    const directiveBtn = screen.getByText('Simple Data Analysis');
    fireEvent.click(directiveBtn);
    
    expect(textarea.value).toBe('');
  });

  it('dispatches a directive successfully', async () => {
    render(
      <DirectiveModal isOpen={true} onClose={mockOnClose} graphs={mockGraphs} />
    );
    
    // Select a directive
    fireEvent.click(screen.getByText('Simple Data Analysis'));
    
    // Click dispatch
    const dispatchBtn = screen.getByText('Dispatch Directive');
    fireEvent.click(dispatchBtn);
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/operations/directive/execute'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ graph_id: 'simple_data_analysis' })
        })
      );
      expect(mockShowToast).toHaveBeenCalledWith('Directive dispatched to Kowalski', 'success');
    });
  });

  it('dispatches a manual prompt successfully', async () => {
    render(
      <DirectiveModal isOpen={true} onClose={mockOnClose} graphs={mockGraphs} />
    );
    
    const textarea = screen.getByPlaceholderText(/Enter custom instructions/i);
    fireEvent.change(textarea, { target: { value: 'Fix the code' } });
    
    const dispatchBtn = screen.getByText('Dispatch Directive');
    fireEvent.click(dispatchBtn);
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/operations/directive/execute'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ manual_prompt: 'Fix the code' })
        })
      );
    });
  });

  it('shows error toast on API failure', async () => {
    global.fetch = vi.fn().mockImplementation(() => 
      Promise.resolve({ ok: false })
    );

    render(
      <DirectiveModal isOpen={true} onClose={mockOnClose} graphs={mockGraphs} />
    );
    
    fireEvent.click(screen.getByText('Simple Data Analysis'));
    fireEvent.click(screen.getByText('Dispatch Directive'));
    
    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith('Failed to dispatch directive.', 'error');
    });
  });
});

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DirectiveModal } from '@/modules/ui/DirectiveModal';
import { useToast } from '@/modules/ui/ToastProvider';
import { TerminalProvider } from '@/modules/TerminalContext';
import { NotificationProvider } from '@/modules/NotificationContext';
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

// Helper to wrap modal with required providers
const renderModal = (props: Parameters<typeof DirectiveModal>[0]) =>
  render(
    <NotificationProvider>
      <TerminalProvider>
        <DirectiveModal {...props} />
      </TerminalProvider>
    </NotificationProvider>
  );

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
    renderModal({ isOpen: true, onClose: mockOnClose, graphs: mockGraphs });
    
    // Modal title is always visible
    expect(screen.getByText('Execute Directive')).toBeDefined();
    // Graph names are behind category tabs — click a category to reveal them
    fireEvent.click(screen.getByText('Analytics'));
    expect(screen.getByText('Simple Data Analysis')).toBeDefined();
    // The manual prompt accordion must be expanded first
    fireEvent.click(screen.getByText('Custom Ad-hoc Directive'));
    expect(screen.getByPlaceholderText(/Enter fully custom, unstructured instructions/i)).toBeDefined();
  });

  it('allows selecting a quick directive', async () => {
    renderModal({ isOpen: true, onClose: mockOnClose, graphs: mockGraphs });
    
    // Expand the Analytics category tab first
    fireEvent.click(screen.getByText('Analytics'));
    const directiveBtn = screen.getByText('Simple Data Analysis');
    fireEvent.click(directiveBtn);
    
    // The button should show a checkmark (material icon)
    expect(screen.getByText('check_circle')).toBeDefined();
  });

  it('clears manual prompt when a quick directive is selected', () => {
    renderModal({ isOpen: true, onClose: mockOnClose, graphs: mockGraphs });
    
    // Expand the manual accordion first
    fireEvent.click(screen.getByText('Custom Ad-hoc Directive'));
    const textarea = screen.getByPlaceholderText(/Enter fully custom, unstructured instructions/i) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'Manual task' } });
    expect(textarea.value).toBe('Manual task');
    
    // Expand category and select a graph directive
    fireEvent.click(screen.getByText('Analytics'));
    const directiveBtn = screen.getByText('Simple Data Analysis');
    fireEvent.click(directiveBtn);
    
    // Selecting a graph clears the manual prompt
    expect(textarea.value).toBe('');
  });

  it('dispatches a directive successfully', async () => {
    renderModal({ isOpen: true, onClose: mockOnClose, graphs: mockGraphs });
    
    // Select a directive through category tab
    fireEvent.click(screen.getByText('Analytics'));
    fireEvent.click(screen.getByText('Simple Data Analysis'));
    
    // Click dispatch
    const dispatchBtn = screen.getByText('Dispatch Directive');
    fireEvent.click(dispatchBtn);
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/operations/directive/execute'),
        expect.objectContaining({
          method: 'POST',
        })
      );
      // Success screen should be visible instead of calling toast
      expect(screen.getByText('Mission Dispatched')).toBeDefined();
      expect(screen.getByText(/Directive received and queued for execution/i)).toBeDefined();
    });
  });

  it('dispatches a manual prompt successfully', async () => {
    renderModal({ isOpen: true, onClose: mockOnClose, graphs: mockGraphs });
    
    // Expand the manual accordion
    fireEvent.click(screen.getByText('Custom Ad-hoc Directive'));
    const textarea = screen.getByPlaceholderText(/Enter fully custom, unstructured instructions/i);
    fireEvent.change(textarea, { target: { value: 'Fix the code' } });
    
    const dispatchBtn = screen.getByText('Dispatch Directive');
    fireEvent.click(dispatchBtn);
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/operations/directive/execute'),
        expect.objectContaining({
          method: 'POST',
        })
      );
      // Success screen should be visible
      expect(screen.getByText('Mission Dispatched')).toBeDefined();
    });
  });

  it('shows error toast on API failure', async () => {
    global.fetch = vi.fn().mockImplementation(() => 
      Promise.resolve({ ok: false })
    );

    renderModal({ isOpen: true, onClose: mockOnClose, graphs: mockGraphs });
    
    // Select a directive via category tab
    fireEvent.click(screen.getByText('Analytics'));
    fireEvent.click(screen.getByText('Simple Data Analysis'));
    fireEvent.click(screen.getByText('Dispatch Directive'));
    
    await waitFor(() => {
      expect(mockShowToast).toHaveBeenCalledWith('Failed to dispatch directive.', 'error');
    });
  });
});

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { AgentEditModal } from '@/modules/AgentEditModal';
import { FamigliaAgent } from '@/types';

const mockAgent: FamigliaAgent = {
  id: 'alfredo',
  agent_id: 'alfredo',
  name: 'Alfredo',
  role: 'Chief of Staff',
  is_active: true,
  status: 'active',
  aliases: ['Butler'],
  personality: 'Traditional and loyal.',
  identity: 'The silent concierge.',
  skills: [],
  skill_ids: [10],
  tools: [],
  tool_ids: [1],
  workflows: [],
  workflow_ids: [100],
  latest_conversation_snippet: 'Yes, Boss.',
  last_active: '2026-03-31T12:00:00Z',
  avatar_url: '/images/alfredo.png'
};

describe('AgentEditModal Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (global as any).fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/capabilities')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            tools: [{ id: 1, name: 'web_search' }],
            skills: [{ id: 10, name: 'Python' }],
            workflows: [{ id: 100, name: 'Onboarding' }]
          }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({ status: 'success' }) });
    });
  });

  it('renders with existing agent data', async () => {
    render(<AgentEditModal agent={mockAgent} onClose={vi.fn()} onSave={vi.fn()} />);
    
    expect(screen.getByText('Edit')).toBeTruthy();
    expect(screen.getByDisplayValue('Alfredo')).toBeTruthy();
    expect(screen.getByText(/The silent concierge\./i)).toBeTruthy();
    expect(screen.getByText('Status: Active')).toBeTruthy();
  });

  it('toggles active status correctly', async () => {
    render(<AgentEditModal agent={mockAgent} onClose={vi.fn()} onSave={vi.fn()} />);
    
    const toggle = screen.getByRole('button', { name: /Toggle Active Status/i });
    fireEvent.click(toggle);
    
    expect(screen.getByText('Status: Inactive')).toBeTruthy();
  });

  it('calls onSave and onClose when clicking Finalize Edits', async () => {
    const onSave = vi.fn();
    const onClose = vi.fn();
    render(<AgentEditModal agent={mockAgent} onClose={onClose} onSave={onSave} />);
    
    const saveButton = screen.getByText('Finalize Edits');
    fireEvent.click(saveButton);
    
    await waitFor(() => {
      expect(onSave).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });
});

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Operations } from '@/modules/Operations';
import type { GraphDefinition, Category, SOPWorkflow } from '@/types';
import React from 'react';

const mockGraphs: GraphDefinition[] = [];
const mockCategories: Category[] = [
  { id: 1, name: 'market_research', display_name: 'Market Research', created_at: new Date().toISOString() },
  { id: 2, name: 'analytics', display_name: 'Analytics', created_at: new Date().toISOString() }
];

const mockWorkflows: SOPWorkflow[] = [
  {
    id: 1,
    name: 'test_sop',
    display_name: 'Test SOP',
    description: 'Test Description',
    category_id: 1,
    node_order: ['node1'],
    nodes: [{ node_name: 'node1', node_type: 'task', description: 'test' }],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  }
];

describe('SOP Hub Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url.includes('/sop/categories')) {
        return Promise.resolve({ ok: true, json: async () => mockCategories });
      }
      if (url.includes('/sop/workflows')) {
        return Promise.resolve({ ok: true, json: async () => mockWorkflows });
      }
      if (url.includes('/actions')) {
        return Promise.resolve({ ok: true, json: async () => ({ actions: [], total: 0 }) });
      }
      if (url.includes('/operations/mission-logs/all')) {
        return Promise.resolve({ ok: true, json: async () => [] });
      }
      if (url.includes('/chat/conversations')) {
        return Promise.resolve({ ok: true, json: async () => [] });
      }
      return Promise.resolve({ 
        ok: true, 
        json: async () => ({ actions: [], total: 0 }) 
      });
    }));
  });

  it('switches to SOP Hub and displays categories', async () => {
    render(<Operations graphs={mockGraphs} selectedGraph={null} setSelectedGraph={vi.fn()} initialTasks={[]} />);
    
    // Click SOP Hub tab
    const sopTab = await screen.findByText(/SOP Hub/i);
    fireEvent.click(sopTab);
    
    // Wait for categories to load via test-id
    expect(await screen.findByTestId('category-header-market_research')).toBeDefined();
    expect(await screen.findByTestId('category-header-analytics')).toBeDefined();
    
    // Check for "Test SOP" protocol title via test-id
    expect(await screen.findByTestId('sop-title-test_sop')).toBeDefined();
  });

  it('opens Category Creator from Initialize Protocol menu', async () => {
    render(<Operations graphs={mockGraphs} selectedGraph={null} setSelectedGraph={vi.fn()} initialTasks={[]} />);
    
    // Switch to SOP Hub
    fireEvent.click(await screen.findByText(/SOP Hub/i));
    
    // Open menu
    const initBtn = await screen.findByText(/Initialize Protocol/i);
    fireEvent.click(initBtn);
    
    // Click Add New Category
    const addCatBtn = await screen.findByText(/Add New Category/i);
    fireEvent.click(addCatBtn);
    
    // Check for Category Creator header
    const header = await screen.findByRole('heading', { name: /Initialize Structural Tier/i });
    expect(header).toBeDefined();
  });

  it('opens SOP Builder from Initialize Protocol menu', async () => {
    render(<Operations graphs={mockGraphs} selectedGraph={null} setSelectedGraph={vi.fn()} initialTasks={[]} />);
    
    // Switch to SOP Hub
    fireEvent.click(await screen.findByText(/SOP Hub/i));
    
    // Open menu
    const initBtn = await screen.findByText(/Initialize Protocol/i);
    fireEvent.click(initBtn);
    
    // Click Draft New SOP
    const draftBtn = await screen.findByText(/Draft New SOP/i);
    fireEvent.click(draftBtn);
    
    // Check for SOP Architect header
    const header = await screen.findByRole('heading', { name: /SOP Architect/i });
    expect(header).toBeDefined();
  });
});

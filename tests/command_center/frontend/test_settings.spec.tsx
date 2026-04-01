import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Settings } from '@/modules/Settings';

describe('Settings Module', () => {
  it('renders honorific and toggles from current settings', () => {
    const onSettingsChange = vi.fn();

    render(
      <Settings
        settings={{
          honorific: 'Donna',
          notificationsEnabled: false,
          backgroundAnimationsEnabled: true,
        }}
        onSettingsChange={onSettingsChange}
      />
    );

    expect(screen.getByPlaceholderText('Custom honorific')).toHaveValue('Donna');
    expect(screen.getByLabelText('Honorific')).toBeDefined();
    expect(screen.getByText('Welcome back, Donna')).toBeDefined();
  });

  it('emits updates when honorific input and toggles change', () => {
    const onSettingsChange = vi.fn();

    render(
      <Settings
        settings={{
          honorific: 'Don',
          notificationsEnabled: true,
          backgroundAnimationsEnabled: true,
        }}
        onSettingsChange={onSettingsChange}
      />
    );

    fireEvent.change(screen.getByPlaceholderText('Custom honorific'), {
      target: { value: 'Boss' },
    });
    expect(onSettingsChange).toHaveBeenCalledWith({
      honorific: 'Boss',
      notificationsEnabled: true,
      backgroundAnimationsEnabled: true,
    });

    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[0]);
    expect(onSettingsChange).toHaveBeenCalledWith({
      honorific: 'Don',
      notificationsEnabled: false,
      backgroundAnimationsEnabled: true,
    });
  });
});

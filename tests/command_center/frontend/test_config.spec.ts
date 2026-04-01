import { describe, it, expect } from 'vitest';
import { BACKEND_BASE, API_BASE } from '@/config';

describe('Frontend Config', () => {
  it('should have a valid BACKEND_BASE', () => {
    expect(BACKEND_BASE).toBe('http://localhost:8000');
  });

  it('should have a valid API_BASE with v1 prefix', () => {
    expect(API_BASE).toBe('http://localhost:8000/api/v1');
  });
});

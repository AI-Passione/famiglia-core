import { describe, it, expect } from 'vitest';
import viteConfig from '../../../src/famiglia_core/command_center/frontend/vite.config';

describe('Vite Config', () => {
  it('should export a configured object', () => {
    // Note: viteConfig may be a function depending on how defineConfig is exported.
    // If it's the direct result or standard exported type, we can assert truthiness.
    expect(viteConfig).toBeDefined();
    
    // Test that plugins are most likely configured
    if (typeof viteConfig !== 'function' && viteConfig.plugins) {
      expect(Array.isArray(viteConfig.plugins)).toBe(true);
    }
  });
});

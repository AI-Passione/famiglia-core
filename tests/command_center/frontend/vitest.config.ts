/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  root: path.resolve(__dirname, '../../../src/famiglia_core/command_center/frontend'),
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: [path.resolve(__dirname, './vitest.setup.ts')],
    include: [path.resolve(__dirname, './**/*.{test,spec}.{ts,tsx}')],
    server: {
      deps: {
        inline: [/framer-motion/],
      }
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '@'),
    },
  },
  server: {
    fs: {
      allow: [path.resolve(__dirname, '../../../')],
    }
  }
});

/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  root: __dirname,
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: [path.resolve(__dirname, './vitest.setup.ts')],
    include: [path.resolve(__dirname, '../../../../tests/command_center/frontend/**/*.{test,spec}.{ts,tsx}')],
    server: {
      deps: {
        inline: [/framer-motion/],
      }
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    fs: {
      allow: [path.resolve(__dirname, '../../../../')],
    }
  }
});

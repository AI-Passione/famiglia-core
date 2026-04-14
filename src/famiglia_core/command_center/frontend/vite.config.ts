import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    // Relative assets work both on repo-scoped Pages URLs and custom domains.
    base: env.VITE_BASE_PATH || './',
    server: {
      host: '0.0.0.0',
      port: 80,
      strictPort: true,
      allowedHosts: true,
      hmr: {
        clientPort: 80,
      },
      watch: {
        usePolling: true,
      },
    },
    build: {
      rollupOptions: {
        input: {
          main: resolve(__dirname, 'index.html'),
          terminal: resolve(__dirname, 'terminal.html'),
          intelligence: resolve(__dirname, 'intelligence.html'),
        },
      },
    },
  }
})

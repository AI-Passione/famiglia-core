import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    // Relative assets work both on repo-scoped Pages URLs and custom domains.
    base: env.VITE_BASE_PATH || './',
  }
})

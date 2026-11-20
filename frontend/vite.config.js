// Copy to frontend/vite.config.js. Collins commits it to the `frontend` branch before anyone starts, so you get it with `git pull`.
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // The API runs on :5000. Proxying /api through Vite keeps the browser on one
  // origin in development, so no CORS_ORIGINS entry is needed locally.
  server: {
    proxy: {
      '/api': { target: 'http://localhost:5000', changeOrigin: true },
    },
  },
})
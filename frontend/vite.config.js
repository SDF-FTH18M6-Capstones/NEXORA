// Copy to frontend/vite.config.js. Collins commits it to the `frontend` branch before anyone starts, so you get it with `git pull`.
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
})
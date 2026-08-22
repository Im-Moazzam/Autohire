/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Docker Desktop on Windows doesn't propagate inotify events through a
    // bind mount, so Vite's default watcher silently misses host-side edits
    // (the file changes on disk but HMR never fires) — polling instead.
    watch: { usePolling: true, interval: 300 },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    globals: true,
  },
})

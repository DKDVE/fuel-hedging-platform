/**
 * DIAGNOSIS: Root cause of frontend→API communication failures in Docker.
 * - Proxy used target localhost:8000 — from frontend container, localhost is NOT the api container.
 * - Missing host: '0.0.0.0' — required for Docker port binding.
 * - No SSE-specific proxy — response buffering breaks EventSource streams.
 * - /api/v1/stream must be matched before /api for correct SSE handling.
 */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0', // required for Docker — binds to all interfaces
    port: 5173,
    proxy: {
      // SSE streams — more specific path first, prevents buffering
      '/api/v1/stream': {
        target: process.env.VITE_PROXY_TARGET || 'http://api:8000',
        changeOrigin: true,
        secure: false,
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('X-Accel-Buffering', 'no')
          })
        },
      },
      // All REST API calls
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://api:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})

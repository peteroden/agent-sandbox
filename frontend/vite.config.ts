import { defineConfig } from 'vite'
import preact from '@preact/preset-vite'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [preact(), tailwindcss()],
  resolve: {
    alias: {
      'react': 'preact/compat',
      'react-dom': 'preact/compat',
      'react/jsx-runtime': 'preact/jsx-runtime',
    },
  },
  // Environment variables are automatically exposed via import.meta.env
  // when prefixed with VITE_. The following are supported:
  // - VITE_OTEL_EXPORTER: 'console' | 'otlp' (default: 'console')
  // - VITE_OTEL_ENDPOINT: OTLP collector URL (default: 'http://localhost:4318')
  // - VITE_OTEL_SAMPLE_RATE: Sampling ratio 0.0-1.0 (default: '1.0')
  // - VITE_SERVICE_NAME: Service name (default: 'agent-sandbox-frontend')
  server: {
    host: true, // Listen on all interfaces for devcontainer access
    proxy: {
      // Proxy OTLP query API for the observe dashboard (must be before /api)
      '/api/observe': {
        target: 'http://localhost:4318',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://0.0.0.0:8888',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        // Ensure trace headers are forwarded (http-proxy does this by default,
        // but explicit is better)
        headers: {
          'X-Forwarded-Proto': 'http',
        },
      },
      '/ag-ui': {
        target: 'http://0.0.0.0:8888',
        changeOrigin: true,
      },
      // Use regex to match /mcp exactly or /mcp/ paths, but NOT /mcp-chat or /mcp-app
      '^/mcp(/|$)': {
        target: 'http://0.0.0.0:8888',
        changeOrigin: true,
        rewrite: (path: string) => path,
      },
      // Proxy OTLP endpoints for browser telemetry (avoids CORS issues)
      '/v1/traces': {
        target: 'http://localhost:4318',
        changeOrigin: true,
      },
      '/v1/logs': {
        target: 'http://localhost:4318',
        changeOrigin: true,
      },
      '/v1/metrics': {
        target: 'http://localhost:4318',
        changeOrigin: true,
      },
    },
  },
})

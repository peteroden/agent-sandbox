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
      // Proxy OTLP endpoints for browser telemetry (avoids CORS issues with SigNoz)
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

import { init } from '@agent-sandbox/otel-web-sdk'
import { renderWithTelemetry } from '@agent-sandbox/otel-web-sdk/react'
import './app.css'
import { App } from './app.tsx'

// Determine endpoint based on exporter type
// - 'console' → use 'console' to trigger console exporter
// - 'otlp' → use VITE_OTEL_ENDPOINT or empty for relative URLs via Vite proxy
const exporter = import.meta.env.VITE_OTEL_EXPORTER || 'console'
const endpoint = exporter === 'console'
  ? 'console'
  : (import.meta.env.VITE_OTEL_ENDPOINT || '')

// Initialize OpenTelemetry before rendering
init({
  serviceName: import.meta.env.VITE_SERVICE_NAME || 'agent-sandbox-frontend',
  endpoint,
  sampleRate: parseFloat(import.meta.env.VITE_OTEL_SAMPLE_RATE || '1.0') || 1.0,
  corsUrls: [
    /localhost:8888/,
    /127\.0\.0\.1:8888/,
    /\/api/,
    /\/mcp/,
    /\/ag-ui/,
  ],
  debug: import.meta.env.DEV,
})

renderWithTelemetry(<App />, document.getElementById('app')!)

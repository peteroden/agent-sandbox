import { render } from 'preact'
import './app.css'
import { App } from './app.tsx'
import { initTelemetry, initWebVitals } from './services/telemetry'
import { OTelErrorBoundary } from './components/OTelErrorBoundary'

// Initialize OpenTelemetry before rendering
initTelemetry()
initWebVitals()

render(
  <OTelErrorBoundary>
    <App />
  </OTelErrorBoundary>,
  document.getElementById('app')!
)

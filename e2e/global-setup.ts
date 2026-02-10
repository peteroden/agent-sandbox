/**
 * Playwright global setup: start the in-memory OTLP collector before tests.
 *
 * The collector must be running before the webServer starts so the backend
 * can export traces to it from startup.
 */
import { startCollector } from './helpers/otlp-collector'

async function globalSetup(): Promise<void> {
  await startCollector()
}

export default globalSetup

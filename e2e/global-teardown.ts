/**
 * Playwright global teardown: stop the in-memory OTLP collector after tests.
 */
import { stopCollector } from './helpers/otlp-collector'

async function globalTeardown(): Promise<void> {
  await stopCollector()
}

export default globalTeardown

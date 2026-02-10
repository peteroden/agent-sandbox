/**
 * Wait for the backend server to respond to health checks.
 *
 * The Playwright webServer config only waits for the frontend (port 5173).
 * The backend (port 8888) may still be starting. Call this in beforeAll
 * for test suites that need the backend.
 */
import { BACKEND_HEALTH_URL, BACKEND_READY_TIMEOUT } from './constants'

export async function waitForBackend(): Promise<void> {
  const interval = 1_000
  const start = Date.now()
  while (Date.now() - start < BACKEND_READY_TIMEOUT) {
    try {
      const resp = await fetch(BACKEND_HEALTH_URL)
      if (resp.ok) return
    } catch {
      /* server not ready yet */
    }
    await new Promise((r) => setTimeout(r, interval))
  }
  throw new Error(
    `Backend server did not become ready at ${BACKEND_HEALTH_URL} within ${BACKEND_READY_TIMEOUT}ms`,
  )
}

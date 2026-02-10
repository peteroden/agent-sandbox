import { test, expect } from '@playwright/test'
import { TraceInterceptor } from '../helpers/trace-interceptor'
import { AgUiResponseCapture } from '../helpers/agui-response-capture'
import { waitForBackend } from '../helpers/wait-for-backend'
import { COLLECTOR_PORT } from '../helpers/otlp-collector'
import {
  CHAT_ROUTE,
  MCP_CHAT_ROUTE,
  ECHO_COMMAND,
  ECHO_EXPECTED,
  RESPONSE_TIMEOUT,
  MCP_CONNECT_TIMEOUT,
} from '../helpers/constants'

const COLLECTOR_URL = `http://localhost:${COLLECTOR_PORT}`
const SPAN_FLUSH_TIMEOUT = 15_000
const SPAN_POLL_INTERVAL = 500

/**
 * Query the in-memory OTLP collector for spans matching a traceId.
 * Returns true if at least one OTLP export contained the traceId bytes.
 */
async function collectorHasTraceId(traceId: string): Promise<boolean> {
  const resp = await fetch(`${COLLECTOR_URL}/api/traces?traceId=${traceId}`)
  const data = (await resp.json()) as { found: boolean }
  return data.found
}

test.describe('Backend trace propagation via OTLP', () => {
  test.beforeAll(async () => {
    await waitForBackend()
  })

  test.beforeEach(async () => {
    await fetch(`${COLLECTOR_URL}/api/traces`, { method: 'DELETE' })
  })

  test('AG-UI Chat: backend exports spans with the browser traceId', async ({ page }) => {
    const interceptor = TraceInterceptor.attach(page)
    const sseCapture = AgUiResponseCapture.attach(page)

    await page.goto(CHAT_ROUTE)
    const input = page.getByPlaceholder('Type a message...')
    await expect(input).toBeVisible()

    await input.fill(ECHO_COMMAND)
    await page.getByRole('button', { name: 'Send' }).click()

    // Wait for the tool call to complete in the UI and SSE stream
    await expect(page.getByText('Tool Call: echo_text')).toBeVisible({
      timeout: RESPONSE_TIMEOUT,
    })
    await expect
      .poll(() => sseCapture.getToolCallResults(), { timeout: RESPONSE_TIMEOUT })
      .toContainEqual(ECHO_EXPECTED)

    // Get the traceId the browser sent
    const traceIds = interceptor.getTraceIds()
    expect(traceIds.length).toBeGreaterThanOrEqual(1)
    const traceId = traceIds[0]

    // Poll the collector until the backend flushes spans with this traceId
    await expect
      .poll(() => collectorHasTraceId(traceId), {
        timeout: SPAN_FLUSH_TIMEOUT,
        intervals: [SPAN_POLL_INTERVAL],
        message: `Expected OTLP collector to receive spans with traceId ${traceId}. ` +
          'If the dev server was reused without OTLP env vars, restart it.',
      })
      .toBe(true)

    interceptor.detach()
    sseCapture.detach()
  })

  test('MCP Chat: backend exports spans with the browser traceId', async ({ page }) => {
    const interceptor = TraceInterceptor.attach(page)

    await page.goto(MCP_CHAT_ROUTE)
    await expect(page.locator('.bg-green-500')).toBeVisible({
      timeout: MCP_CONNECT_TIMEOUT,
    })

    const input = page.getByPlaceholder('Type a message...')
    await expect(input).toBeVisible()

    await input.fill(ECHO_COMMAND)
    await page.getByRole('button', { name: 'Send' }).click()

    await expect(
      page.locator('.bg-gray-100').filter({ hasText: ECHO_EXPECTED }).first(),
    ).toBeVisible({ timeout: RESPONSE_TIMEOUT })

    // Get the traceId the browser sent
    const traceIds = interceptor.getTraceIds()
    expect(traceIds.length).toBeGreaterThanOrEqual(1)
    const traceId = traceIds[0]

    // Poll the collector until the backend flushes spans with this traceId
    await expect
      .poll(() => collectorHasTraceId(traceId), {
        timeout: SPAN_FLUSH_TIMEOUT,
        intervals: [SPAN_POLL_INTERVAL],
        message: `Expected OTLP collector to receive spans with traceId ${traceId}. ` +
          'If the dev server was reused without OTLP env vars, restart it.',
      })
      .toBe(true)

    interceptor.detach()
  })
})

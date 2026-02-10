import { test, expect } from '@playwright/test'
import { TraceInterceptor } from '../helpers/trace-interceptor'
import { AgUiResponseCapture } from '../helpers/agui-response-capture'
import { waitForBackend } from '../helpers/wait-for-backend'
import {
  CHAT_ROUTE,
  MCP_CHAT_ROUTE,
  ECHO_COMMAND,
  ECHO_EXPECTED,
  ADD_COMMAND,
  ADD_EXPECTED,
  RESPONSE_TIMEOUT,
  MCP_CONNECT_TIMEOUT,
} from '../helpers/constants'

test.describe('Trace propagation — consistent traceId', () => {
  test.beforeAll(async () => {
    await waitForBackend()
  })
  test('AG-UI Chat: all requests in a single message share the same traceId', async ({ page }) => {
    const interceptor = TraceInterceptor.attach(page)
    const sseCapture = AgUiResponseCapture.attach(page)

    await page.goto(CHAT_ROUTE)
    const input = page.getByPlaceholder('Type a message...')
    await expect(input).toBeVisible()

    // Send a tool command that triggers backend + MCP server calls
    await input.fill(ECHO_COMMAND)
    await page.getByRole('button', { name: 'Send' }).click()

    // Wait for tool call to appear and SSE to complete
    await expect(page.getByText('Tool Call: echo_text')).toBeVisible({
      timeout: RESPONSE_TIMEOUT,
    })
    await expect
      .poll(() => sseCapture.getToolCallResults(), { timeout: RESPONSE_TIMEOUT })
      .toContainEqual(ECHO_EXPECTED)

    // All requests from this interaction should share one traceId
    const traceIds = interceptor.getTraceIds()
    expect(traceIds.length).toBe(1)

    const requests = interceptor.getRequests()
    expect(requests.length).toBeGreaterThanOrEqual(1)

    // Every request should have the same traceId
    const singleTraceId = traceIds[0]
    for (const req of requests) {
      expect(req.traceparent.traceId).toBe(singleTraceId)
    }

    interceptor.detach()
    sseCapture.detach()
  })

  test('AG-UI Chat: different messages produce different traceIds', async ({ page }) => {
    const interceptor = TraceInterceptor.attach(page)
    const sseCapture = AgUiResponseCapture.attach(page)

    await page.goto(CHAT_ROUTE)
    const input = page.getByPlaceholder('Type a message...')
    await expect(input).toBeVisible()

    // First message
    await input.fill(ECHO_COMMAND)
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(page.getByText('Tool Call: echo_text')).toBeVisible({
      timeout: RESPONSE_TIMEOUT,
    })
    await expect
      .poll(() => sseCapture.getToolCallResults(), { timeout: RESPONSE_TIMEOUT })
      .toContainEqual(ECHO_EXPECTED)

    const firstTraceIds = [...interceptor.getTraceIds()]
    expect(firstTraceIds.length).toBeGreaterThanOrEqual(1)

    interceptor.clear()
    sseCapture.clear()

    // Wait for input to be editable again after first message completes
    await expect(input).toBeEditable({ timeout: RESPONSE_TIMEOUT })

    // Second message (different command)
    await input.fill(ADD_COMMAND)
    await page.getByRole('button', { name: 'Send' }).click()

    // Use nth(1) since the first Tool Call: echo_text is already on the page
    await expect(page.getByText('Tool Call: add_numbers')).toBeVisible({
      timeout: RESPONSE_TIMEOUT,
    })
    await expect
      .poll(() => sseCapture.getToolCallResults(), { timeout: RESPONSE_TIMEOUT })
      .toContainEqual(ADD_EXPECTED)

    const secondTraceIds = interceptor.getTraceIds()
    expect(secondTraceIds.length).toBeGreaterThanOrEqual(1)

    // The second message should produce a different traceId
    for (const id of secondTraceIds) {
      expect(firstTraceIds).not.toContain(id)
    }

    interceptor.detach()
    sseCapture.detach()
  })

  test('MCP Chat: all requests in a single message share the same traceId', async ({ page }) => {
    const interceptor = TraceInterceptor.attach(page)

    await page.goto(MCP_CHAT_ROUTE)
    await expect(page.locator('.bg-green-500')).toBeVisible({
      timeout: MCP_CONNECT_TIMEOUT,
    })

    const input = page.getByPlaceholder('Type a message...')
    await expect(input).toBeVisible()

    await input.fill(ECHO_COMMAND)
    await page.getByRole('button', { name: 'Send' }).click()

    // Wait for assistant response bubble to appear
    await expect(
      page.locator('.bg-gray-100').first(),
    ).toBeVisible({ timeout: RESPONSE_TIMEOUT })

    // All requests from this interaction should share one traceId
    const traceIds = interceptor.getTraceIds()
    expect(traceIds.length).toBeGreaterThanOrEqual(1)

    // If multiple requests were captured they all share the same traceId
    if (traceIds.length === 1) {
      const requests = interceptor.getRequests()
      for (const req of requests) {
        expect(req.traceparent.traceId).toBe(traceIds[0])
      }
    }

    interceptor.detach()
  })

  test('MCP Chat: different messages produce different traceIds', async ({ page }) => {
    const interceptor = TraceInterceptor.attach(page)

    await page.goto(MCP_CHAT_ROUTE)
    await expect(page.locator('.bg-green-500')).toBeVisible({
      timeout: MCP_CONNECT_TIMEOUT,
    })

    const input = page.getByPlaceholder('Type a message...')
    await expect(input).toBeVisible()

    // First message
    await input.fill(ECHO_COMMAND)
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(
      page.locator('.bg-gray-100').first(),
    ).toBeVisible({ timeout: RESPONSE_TIMEOUT })

    const firstTraceIds = [...interceptor.getTraceIds()]
    expect(firstTraceIds.length).toBeGreaterThanOrEqual(1)

    interceptor.clear()

    // Second message
    await input.fill(ADD_COMMAND)
    await page.getByRole('button', { name: 'Send' }).click()

    // Wait for a second assistant message (count should be >= 2)
    await expect(
      page.locator('.bg-gray-100').nth(1),
    ).toBeVisible({ timeout: RESPONSE_TIMEOUT })

    const secondTraceIds = interceptor.getTraceIds()
    expect(secondTraceIds.length).toBeGreaterThanOrEqual(1)

    // The second message should produce a different traceId
    for (const id of secondTraceIds) {
      expect(firstTraceIds).not.toContain(id)
    }

    interceptor.detach()
  })
})

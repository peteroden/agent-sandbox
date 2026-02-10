import { test, expect } from '@playwright/test'
import { TraceInterceptor } from '../helpers/trace-interceptor'
import { AgUiResponseCapture } from '../helpers/agui-response-capture'
import {
  CHAT_ROUTE,
  ECHO_COMMAND,
  ECHO_EXPECTED,
  RESPONSE_TIMEOUT,
} from '../helpers/constants'

test.describe('AG-UI Chat — echo_text', () => {
  test('sends echo command and receives expected response', async ({ page }) => {
    const traceInterceptor = TraceInterceptor.attach(page)
    const sseCapture = AgUiResponseCapture.attach(page)

    await page.goto(CHAT_ROUTE)

    // react-ag-ui renders a textarea with this placeholder
    const input = page.getByPlaceholder('Type a message...')
    await expect(input).toBeVisible()

    await input.fill(ECHO_COMMAND)
    await page.getByRole('button', { name: 'Send' }).click()

    // Wait for the tool call section to appear in react-ag-ui
    await expect(page.getByText('Tool Call: echo_text')).toBeVisible({
      timeout: RESPONSE_TIMEOUT,
    })

    // Verify the SSE stream contains the correct tool result
    // (react-ag-ui may not render it, but the data is correct)
    await expect
      .poll(() => sseCapture.getToolCallResults(), { timeout: RESPONSE_TIMEOUT })
      .toContainEqual(ECHO_EXPECTED)

    // Verify traceparent was sent to the backend
    const traceIds = traceInterceptor.getTraceIds()
    expect(traceIds.length).toBeGreaterThanOrEqual(1)

    // Validate trace ID format (32-char hex)
    for (const id of traceIds) {
      expect(id).toMatch(/^[0-9a-f]{32}$/)
    }

    traceInterceptor.detach()
    sseCapture.detach()
  })
})

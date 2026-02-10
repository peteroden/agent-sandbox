import { test, expect } from '@playwright/test'
import { TraceInterceptor } from '../helpers/trace-interceptor'
import { AgUiResponseCapture } from '../helpers/agui-response-capture'
import {
  CHAT_ROUTE,
  ADD_COMMAND,
  ADD_EXPECTED,
  RESPONSE_TIMEOUT,
} from '../helpers/constants'

test.describe('AG-UI Chat — add_numbers', () => {
  test('sends add command and receives expected result', async ({ page }) => {
    const traceInterceptor = TraceInterceptor.attach(page)
    const sseCapture = AgUiResponseCapture.attach(page)

    await page.goto(CHAT_ROUTE)

    const input = page.getByPlaceholder('Type a message...')
    await expect(input).toBeVisible()

    await input.fill(ADD_COMMAND)
    await page.getByRole('button', { name: 'Send' }).click()

    // Wait for the tool call section to appear in react-ag-ui
    await expect(page.getByText('Tool Call: add_numbers')).toBeVisible({
      timeout: RESPONSE_TIMEOUT,
    })

    // Verify the SSE stream contains the correct tool result
    await expect
      .poll(() => sseCapture.getToolCallResults(), { timeout: RESPONSE_TIMEOUT })
      .toContainEqual(ADD_EXPECTED)

    // Verify traceparent was sent
    const traceIds = traceInterceptor.getTraceIds()
    expect(traceIds.length).toBeGreaterThanOrEqual(1)

    for (const id of traceIds) {
      expect(id).toMatch(/^[0-9a-f]{32}$/)
    }

    traceInterceptor.detach()
    sseCapture.detach()
  })
})

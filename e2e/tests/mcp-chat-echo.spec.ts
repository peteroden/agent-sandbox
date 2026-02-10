import { test, expect } from '@playwright/test'
import { TraceInterceptor } from '../helpers/trace-interceptor'
import {
  MCP_CHAT_ROUTE,
  ECHO_COMMAND,
  ECHO_EXPECTED,
  RESPONSE_TIMEOUT,
  MCP_CONNECT_TIMEOUT,
} from '../helpers/constants'

test.describe('MCP Chat — echo_text', () => {
  test('sends echo command via MCP and receives the echo result', async ({ page }) => {
    const interceptor = TraceInterceptor.attach(page)

    await page.goto(MCP_CHAT_ROUTE)

    // Wait for MCP connection (green indicator dot)
    await expect(page.locator('.bg-green-500')).toBeVisible({
      timeout: MCP_CONNECT_TIMEOUT,
    })

    const input = page.getByPlaceholder('Type a message...')
    await expect(input).toBeVisible()

    await input.fill(ECHO_COMMAND)
    await page.getByRole('button', { name: 'Send' }).click()

    // Wait for assistant response containing the echo result text
    await expect(
      page.locator('.bg-gray-100').filter({ hasText: ECHO_EXPECTED }).first(),
    ).toBeVisible({ timeout: RESPONSE_TIMEOUT })

    // Verify traceparent headers were sent to /mcp
    const traceIds = interceptor.getTraceIds()
    expect(traceIds.length).toBeGreaterThanOrEqual(1)

    for (const id of traceIds) {
      expect(id).toMatch(/^[0-9a-f]{32}$/)
    }

    interceptor.detach()
  })
})

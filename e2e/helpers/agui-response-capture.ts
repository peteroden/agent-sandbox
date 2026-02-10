import type { Page, Response } from '@playwright/test'

/**
 * Parsed AG-UI Server-Sent Event.
 */
export interface AgUiEvent {
  type: string
  [key: string]: unknown
}

/**
 * Captures and parses AG-UI SSE responses from POST /ag-ui requests.
 *
 * The AG-UI protocol returns Server-Sent Events in the format:
 *   data: {"type":"TOOL_CALL_RESULT","content":"Echo: hello world",...}
 *
 * This helper intercepts the response body and parses all events.
 */
export class AgUiResponseCapture {
  private readonly events: AgUiEvent[][] = []
  private readonly page: Page

  private constructor(page: Page) {
    this.page = page
    this.page.on('response', this.handleResponse)
  }

  static attach(page: Page): AgUiResponseCapture {
    return new AgUiResponseCapture(page)
  }

  detach(): void {
    this.page.off('response', this.handleResponse)
  }

  /** Get all captured event sequences (one per request). */
  getAllEventSequences(): readonly AgUiEvent[][] {
    return [...this.events]
  }

  /** Get all events from all captured requests, flattened. */
  getAllEvents(): AgUiEvent[] {
    return this.events.flat()
  }

  /** Find events by type across all captured requests. */
  findEventsByType(type: string): AgUiEvent[] {
    return this.getAllEvents().filter((e) => e.type === type)
  }

  /** Get the content/text from TOOL_CALL_RESULT events.
   *
   * Handles both plain-text results ("Echo: hello world") and
   * MCP-style JSON results ([{"type":"text","text":"Echo: hello world"}]).
   */
  getToolCallResults(): string[] {
    return this.findEventsByType('TOOL_CALL_RESULT')
      .map((e) => {
        const raw = (e.content as string) ?? ''
        if (!raw) return ''
        // Try to parse MCP-style JSON array
        try {
          const parsed: unknown = JSON.parse(raw)
          if (Array.isArray(parsed)) {
            const texts = parsed
              .filter(
                (item): item is { text: string } =>
                  typeof item === 'object' &&
                  item !== null &&
                  'text' in item &&
                  typeof (item as { text: unknown }).text === 'string',
              )
              .map((item) => item.text)
            if (texts.length > 0) return texts.join(' ')
          }
        } catch {
          // Not JSON — use as-is
        }
        return raw
      })
      .filter(Boolean)
  }

  /** Clear all captured data. */
  clear(): void {
    this.events.length = 0
  }

  /** Parse an SSE response body into AgUiEvents. */
  static parseSseBody(body: string): AgUiEvent[] {
    const events: AgUiEvent[] = []
    const lines = body.split('\n')
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data: ')) continue
      const jsonStr = trimmed.slice(6) // Remove "data: " prefix
      try {
        const parsed = JSON.parse(jsonStr) as AgUiEvent
        if (parsed.type) {
          events.push(parsed)
        }
      } catch {
        // Skip non-JSON lines
      }
    }
    return events
  }

  private readonly handleResponse = async (response: Response): Promise<void> => {
    const url = response.url()
    if (!url.includes('/ag-ui')) return
    if (response.request().method() !== 'POST') return

    try {
      const body = await response.text()
      const events = AgUiResponseCapture.parseSseBody(body)
      if (events.length > 0) {
        this.events.push(events)
      }
    } catch {
      // Response body may not be available in all cases
    }
  }
}

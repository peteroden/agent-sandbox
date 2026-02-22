import type { Page, Request } from '@playwright/test'

/** Parsed W3C traceparent header fields. */
export interface TraceparentInfo {
  /** Full traceparent header value (e.g. "00-abc123...-def456...-01") */
  raw: string
  /** 32-char hex trace ID */
  traceId: string
  /** 16-char hex span/parent ID */
  spanId: string
  /** 2-char hex flags */
  flags: string
}

/** A captured request with its traceparent header. */
export interface TracedRequest {
  url: string
  method: string
  traceparent: TraceparentInfo
}

const TRACEPARENT_RE = /^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$/

/**
 * Intercepts outgoing HTTP requests from a Playwright page and captures
 * any W3C `traceparent` headers sent to the backend endpoints.
 *
 * Usage:
 * ```ts
 * const interceptor = TraceInterceptor.attach(page)
 * // ... interact with the page ...
 * const ids = interceptor.getTraceIds()
 * ```
 */
export class TraceInterceptor {
  private readonly captured: TracedRequest[] = []
  private readonly urlPatterns: RegExp[]

  private constructor(
    private readonly page: Page,
    urlPatterns: RegExp[],
  ) {
    this.urlPatterns = urlPatterns
    this.page.on('request', this.handleRequest)
  }

  /**
   * Attach a trace interceptor to a Playwright page.
   *
   * @param page - Playwright page instance
   * @param urlPatterns - URL patterns to intercept (defaults to /ag-ui and /mcp endpoints)
   */
  static attach(
    page: Page,
    urlPatterns: RegExp[] = [/\/ag-ui/, /\/mcp/],
  ): TraceInterceptor {
    return new TraceInterceptor(page, urlPatterns)
  }

  /** Stop intercepting requests. */
  detach(): void {
    this.page.off('request', this.handleRequest)
  }

  /** Get all captured traced requests. */
  getRequests(): readonly TracedRequest[] {
    return [...this.captured]
  }

  /** Get all unique trace IDs captured so far. */
  getTraceIds(): string[] {
    const ids = new Set(this.captured.map((r) => r.traceparent.traceId))
    return [...ids]
  }

  /** Get all requests sharing a specific trace ID. */
  getRequestsForTrace(traceId: string): TracedRequest[] {
    return this.captured.filter((r) => r.traceparent.traceId === traceId)
  }

  /** Reset captured data between test cases. */
  clear(): void {
    this.captured.length = 0
  }

  /**
   * Parse a raw traceparent header value into its components.
   * Returns null if the header doesn't match W3C format.
   */
  static parseTraceparent(value: string): TraceparentInfo | null {
    const match = TRACEPARENT_RE.exec(value)
    if (!match) return null
    return {
      raw: value,
      traceId: match[1],
      spanId: match[2],
      flags: match[3],
    }
  }

  private readonly handleRequest = (request: Request): void => {
    const url = request.url()
    const matchesPattern = this.urlPatterns.some((pattern) => pattern.test(url))
    if (!matchesPattern) return

    const traceparent = request.headers()['traceparent']
    if (!traceparent) return

    const parsed = TraceInterceptor.parseTraceparent(traceparent)
    if (!parsed) return

    this.captured.push({
      url,
      method: request.method(),
      traceparent: parsed,
    })
  }
}

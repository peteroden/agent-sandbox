/**
 * @fileoverview Span management utilities.
 *
 * Provides helpers for creating and managing trace spans.
 */
import {
  trace,
  context,
  SpanStatusCode,
  type Span,
  type SpanOptions,
  type Attributes,
  type Context,
} from '@opentelemetry/api'

// Re-export types for convenience
export { SpanStatusCode }
export type { Span, SpanOptions, Attributes }

/**
 * Get the tracer for creating spans.
 */
function getTracer() {
  return trace.getTracer(__PKG_NAME__, __PKG_VERSION__)
}

/**
 * Start a new span for tracing an operation.
 *
 * Remember to call span.end() when the operation is complete.
 * For automatic span management, use withSpan() instead.
 *
 * @param name - Name of the span/operation
 * @param options - Optional span options (attributes, links, etc.)
 * @param parentContext - Optional parent context for the span
 * @returns The created span
 *
 * @example
 * ```ts
 * const span = startSpan('my-operation')
 * try {
 *   // Do work
 * } finally {
 *   span.end()
 * }
 * ```
 */
export function startSpan(name: string, options?: SpanOptions, parentContext?: Context): Span {
  return getTracer().startSpan(name, options, parentContext)
}

/**
 * Get the currently active span, if any.
 *
 * @returns The active span or undefined if none is active
 */
export function getActiveSpan(): Span | undefined {
  return trace.getActiveSpan()
}

/**
 * Execute a function within a span context.
 *
 * Automatically:
 * - Creates and starts the span
 * - Sets the span as active in the context
 * - Records exceptions if the function throws
 * - Sets error status on failure
 * - Ends the span when complete
 *
 * @param name - Name of the span/operation
 * @param fn - Function to execute (receives the span as argument)
 * @returns The result of the function
 *
 * @example
 * ```ts
 * const result = await withSpan('fetch-data', async (span) => {
 *   span.setAttribute('url', '/api/data')
 *   const response = await fetch('/api/data')
 *   return response.json()
 * })
 * ```
 */
export async function withSpan<T>(
  name: string,
  fn: (span: Span) => T | Promise<T>
): Promise<T> {
  const span = startSpan(name)

  try {
    const result = await context.with(
      trace.setSpan(context.active(), span),
      () => fn(span)
    )
    span.setStatus({ code: SpanStatusCode.OK })
    return result
  } catch (error) {
    span.recordException(error as Error)
    span.setStatus({
      code: SpanStatusCode.ERROR,
      message: (error as Error).message,
    })
    throw error
  } finally {
    span.end()
  }
}

/**
 * Add an event to the currently active span.
 *
 * Does nothing if no span is active.
 *
 * @param name - Event name
 * @param attributes - Optional event attributes
 */
export function addSpanEvent(name: string, attributes?: Attributes): void {
  const span = getActiveSpan()
  span?.addEvent(name, attributes)
}

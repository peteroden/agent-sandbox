import type { Attributes } from '@opentelemetry/api'
import { SpanStatusCode } from '@opentelemetry/api'
import { getTracer } from '../services/telemetry'

/**
 * Wrap an async function with OpenTelemetry span lifecycle management.
 *
 * Automatically:
 * - Creates and starts a span with the given name
 * - Sets optional attributes on the span
 * - Sets span status to OK on success
 * - Records exceptions and sets ERROR status on failure
 * - Ends the span when complete (success or failure)
 *
 * @typeParam T - The return type of the wrapped function
 * @param name - Name of the span/operation
 * @param fn - Async function to execute within the span
 * @param attributes - Optional attributes to set on the span
 * @returns The result of the wrapped function
 * @throws Re-throws any error from the wrapped function
 *
 * @example
 * ```typescript
 * const result = await withTelemetry(
 *   'api.fetch_users',
 *   async () => {
 *     const response = await fetch('/api/users');
 *     return response.json();
 *   },
 *   { 'api.endpoint': '/users' }
 * );
 * ```
 */
export async function withTelemetry<T>(
  name: string,
  fn: () => Promise<T>,
  attributes?: Attributes
): Promise<T> {
  const tracer = getTracer()
  const span = tracer.startSpan(name, { attributes })

  try {
    const result = await fn()
    span.setStatus({ code: SpanStatusCode.OK })
    return result
  } catch (error) {
    const err = error as Error
    span.recordException(err)
    span.setStatus({
      code: SpanStatusCode.ERROR,
      message: err.message,
    })
    throw error
  } finally {
    span.end()
  }
}

import { useMemo, useCallback } from 'preact/hooks'
import type { Span, Attributes } from '@opentelemetry/api'
import { getTracer, getSessionId, logger } from '../services/telemetry'

/**
 * Return type for useTelemetry hook
 */
export interface UseTelemetryReturn {
  /** Create a new span for tracing an operation */
  createSpan: (name: string, attributes?: Attributes) => Span
  /** Structured logger with debug, info, warn, error methods */
  logger: typeof logger
  /** Current session ID for this browser session */
  sessionId: string | null
}

/**
 * Hook providing access to telemetry primitives.
 *
 * Exposes tracer, logger, and session ID for consistent instrumentation
 * across any UI component.
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { createSpan, logger, sessionId } = useTelemetry();
 *
 *   const handleClick = () => {
 *     const span = createSpan('button.click', { 'button.id': 'submit' });
 *     try {
 *       // ... do work
 *       logger.info('Button clicked', { 'session.id': sessionId ?? '' });
 *     } finally {
 *       span.end();
 *     }
 *   };
 *
 *   return <button onClick={handleClick}>Click</button>;
 * }
 * ```
 */
export function useTelemetry(): UseTelemetryReturn {
  const createSpan = useCallback((name: string, attributes?: Attributes): Span => {
    const tracer = getTracer()
    return tracer.startSpan(name, { attributes })
  }, [])

  const sessionId = useMemo(() => getSessionId(), [])

  // Logger is a stable module-level object, so we can return it directly
  // We wrap it in useMemo to ensure stable reference for the return object
  return useMemo(() => ({
    createSpan,
    logger,
    sessionId,
  }), [createSpan, sessionId])
}

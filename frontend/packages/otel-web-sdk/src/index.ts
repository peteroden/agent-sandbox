/**
 * @fileoverview OpenTelemetry Web SDK main exports.
 *
 * @example
 * ```ts
 * import { init, logger, withSpan, trackEvent } from '@agent-sandbox/otel-web-sdk'
 *
 * init({
 *   serviceName: 'my-app',
 *   endpoint: 'http://localhost:4318',
 * })
 *
 * await withSpan('my-operation', async (span) => {
 *   logger.info('Starting operation')
 *   // ... do work
 *   trackEvent('operation_complete')
 * })
 * ```
 */

// Initialization
export { init, shutdown, isInitialized, getSessionId, sanitizePath } from './init'
export type { InitOptions } from './init'

// Logger
export { logger } from './logger'
export type { LogAttrs } from './logger'

// Spans
export {
  startSpan,
  getActiveSpan,
  withSpan,
  addSpanEvent,
  SpanStatusCode,
} from './spans'
export type { Span, SpanOptions, Attributes } from './spans'

// User tracking
export { setUser, clearUser, getUser } from './user'
export type { UserInfo } from './user'

// Events
export { trackEvent } from './events'

// Errors
export { trackError } from './errors'

// Metrics
export { trackMetric } from './metrics'

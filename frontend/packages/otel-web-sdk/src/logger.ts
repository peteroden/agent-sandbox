/**
 * @fileoverview Auto-correlating logger.
 *
 * Logs automatically inherit active trace context without
 * requiring manual span parameter passing. Optionally accepts
 * a span for explicit correlation.
 */
import { context, trace, type Span } from '@opentelemetry/api'
import { SeverityNumber, type Logger } from '@opentelemetry/api-logs'
import { _getLoggerProvider, _isDebug } from './init'

/** Log attributes type */
export type LogAttrs = Record<string, string | number | boolean | undefined>

/**
 * Get the OTel logger instance.
 */
function getOtelLogger(): Logger | null {
  const provider = _getLoggerProvider()
  if (!provider) {
    if (_isDebug()) {
      console.warn('[OTel SDK] logger called before init()')
    }
    return null
  }
  return provider.getLogger(__PKG_NAME__)
}

/**
 * Emit a log record with the given severity.
 * Uses provided span context or falls back to active span context.
 *
 * @param severityNumber - OTel severity level
 * @param message - Log message
 * @param attrs - Optional log attributes
 * @param span - Optional span for explicit correlation
 */
function emitLog(
  severityNumber: SeverityNumber,
  message: string,
  attrs?: LogAttrs,
  span?: Span
): void {
  const otelLogger = getOtelLogger()
  if (!otelLogger) return

  // Filter out undefined values from attributes
  const cleanAttrs = attrs
    ? Object.fromEntries(
        Object.entries(attrs).filter(([, v]) => v !== undefined)
      )
    : undefined

  // Use provided span's context or fall back to active context
  const logContext = span
    ? trace.setSpan(context.active(), span)
    : context.active()

  otelLogger.emit({
    severityNumber,
    body: message,
    attributes: cleanAttrs,
    context: logContext,
  })
}

/**
 * Auto-correlating logger.
 *
 * Logs automatically inherit the active trace context.
 * Optionally pass a span for explicit correlation.
 *
 * @example
 * ```ts
 * import { logger, startSpan } from '@agent-sandbox/otel-web-sdk'
 *
 * // Auto-correlate with active trace
 * logger.info('User logged in', { userId: '123' })
 *
 * // Explicit span correlation
 * const span = startSpan('my-operation')
 * logger.info('Operation started', { step: 1 }, span)
 * span.end()
 * ```
 */
export const logger = {
  /**
   * Log a debug message.
   * @param message - Log message
   * @param attrs - Optional attributes
   * @param span - Optional span for explicit correlation
   */
  debug: (message: string, attrs?: LogAttrs, span?: Span): void =>
    emitLog(SeverityNumber.DEBUG, message, attrs, span),

  /**
   * Log an info message.
   * @param message - Log message
   * @param attrs - Optional attributes
   * @param span - Optional span for explicit correlation
   */
  info: (message: string, attrs?: LogAttrs, span?: Span): void =>
    emitLog(SeverityNumber.INFO, message, attrs, span),

  /**
   * Log a warning message.
   * @param message - Log message
   * @param attrs - Optional attributes
   * @param span - Optional span for explicit correlation
   */
  warn: (message: string, attrs?: LogAttrs, span?: Span): void =>
    emitLog(SeverityNumber.WARN, message, attrs, span),

  /**
   * Log an error message.
   * @param message - Log message
   * @param attrs - Optional attributes
   * @param span - Optional span for explicit correlation
   */
  error: (message: string, attrs?: LogAttrs, span?: Span): void =>
    emitLog(SeverityNumber.ERROR, message, attrs, span),
}

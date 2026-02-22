/**
 * @fileoverview Error tracking module.
 */
import { context } from '@opentelemetry/api'
import { SeverityNumber } from '@opentelemetry/api-logs'
import { _getLoggerProvider, _isDebug, sanitizePath } from './init'

/**
 * Track an error with optional context.
 *
 * Stack traces are automatically sanitized to remove potential PII.
 *
 * @param error - The error to track
 * @param errorContext - Optional context about where/why the error occurred
 *
 * @example
 * ```ts
 * try {
 *   await riskyOperation()
 * } catch (error) {
 *   trackError(error as Error, { component: 'UserForm', action: 'submit' })
 * }
 * ```
 */
export function trackError(
  error: Error,
  errorContext?: Record<string, string>
): void {
  const loggerProvider = _getLoggerProvider()
  if (!loggerProvider) {
    if (_isDebug()) {
      console.warn('[OTel SDK] trackError called before init()')
    }
    return
  }

  // Sanitize error stack to remove potential PII
  const sanitizedStack = sanitizePath(error.stack)

  const logger = loggerProvider.getLogger('errors')
  logger.emit({
    severityNumber: SeverityNumber.ERROR,
    body: error.message,
    attributes: {
      'error.type': error.name,
      'error.stack': sanitizedStack,
      ...errorContext,
    },
    context: context.active(),
  })
}

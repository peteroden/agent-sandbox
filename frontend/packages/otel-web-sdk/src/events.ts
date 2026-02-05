/**
 * @fileoverview Event tracking module.
 *
 * Events are implemented as structured log entries, delegating to the logger.
 */
import { logger } from './logger'

/**
 * Track a custom event.
 *
 * Events are emitted as INFO-level log entries with structured attributes.
 *
 * @param name - Event name (e.g., 'button_click', 'form_submit')
 * @param attributes - Optional key-value pairs for event context
 *
 * @example
 * ```ts
 * trackEvent('button_click', { element: 'submit-btn', page: '/checkout' })
 * ```
 */
export function trackEvent(
  name: string,
  attributes?: Record<string, string>
): void {
  if (!name || typeof name !== 'string') return

  logger.info(name, {
    'event.name': name,
    ...attributes,
  })
}

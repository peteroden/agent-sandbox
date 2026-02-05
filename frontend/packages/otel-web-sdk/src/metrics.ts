/**
 * @fileoverview Metrics tracking module.
 *
 * Note: OpenTelemetry SDK internally caches instruments by name,
 * so we don't need our own cache layer.
 */
import { _getMeterProvider, _isDebug } from './init'

/**
 * Track a metric value.
 *
 * @param name - Metric name (e.g., 'api_latency', 'cache_hit_rate')
 * @param value - Numeric value to record (must be finite number)
 * @param attributes - Optional attributes for the metric
 *
 * @example
 * ```ts
 * // Track API latency
 * const start = performance.now()
 * await fetch('/api/data')
 * trackMetric('api_latency', performance.now() - start, { endpoint: '/api/data' })
 * ```
 */
export function trackMetric(
  name: string,
  value: number,
  attributes?: Record<string, string>
): void {
  if (!name || typeof name !== 'string') return
  if (!Number.isFinite(value)) return

  const meterProvider = _getMeterProvider()
  if (!meterProvider) {
    if (_isDebug()) {
      console.warn('[OTel SDK] trackMetric called before init()')
    }
    return
  }

  meterProvider.getMeter('metrics').createHistogram(name).record(value, attributes)
}

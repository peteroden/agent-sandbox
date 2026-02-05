/**
 * @fileoverview Tests for metrics tracking.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Test constants
const TEST_SERVICE_NAME = 'test-metrics-service'
const TEST_METRIC_NAME = 'api_latency'

describe('metrics', () => {
  beforeEach(() => {
    vi.resetModules()

    // Reset global state
    delete (globalThis as Record<string, unknown>).__otelFetchWrapped
    delete (globalThis as Record<string, unknown>).__otelInjectHeaders
  })

  afterEach(async () => {
    const { shutdown, isInitialized } = await import('../src/init')
    if (isInitialized()) {
      await shutdown()
    }
  })

  it('trackMetric is no-op when SDK not initialized', async () => {
    // Arrange
    const { trackMetric } = await import('../src/metrics')

    // Act: Should not throw
    expect(() => trackMetric(TEST_METRIC_NAME, 42)).not.toThrow()
  })

  it('trackMetric records metric when SDK is initialized', async () => {
    // Arrange
    const { init } = await import('../src/init')
    const { trackMetric } = await import('../src/metrics')

    init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

    // Act: Should not throw
    expect(() => trackMetric(TEST_METRIC_NAME, 150)).not.toThrow()
  })

  it('trackMetric accepts optional attributes', async () => {
    // Arrange
    const { init } = await import('../src/init')
    const { trackMetric } = await import('../src/metrics')

    init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

    // Act
    expect(() => trackMetric(TEST_METRIC_NAME, 200, {
      endpoint: '/api/users',
      method: 'GET',
    })).not.toThrow()
  })

  it('trackMetric accepts various numeric values', async () => {
    // Arrange
    const { init } = await import('../src/init')
    const { trackMetric } = await import('../src/metrics')

    init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

    // Act: Various numeric values
    expect(() => trackMetric('count', 0)).not.toThrow()
    expect(() => trackMetric('latency', 0.5)).not.toThrow()
    expect(() => trackMetric('negative', -10)).not.toThrow()
  })
})

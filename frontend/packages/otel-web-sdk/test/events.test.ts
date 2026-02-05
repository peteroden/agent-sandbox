/**
 * @fileoverview Tests for event tracking.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Test constants
const TEST_SERVICE_NAME = 'test-events-service'
const TEST_EVENT_NAME = 'button_click'

describe('events', () => {
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

  it('trackEvent is no-op when SDK not initialized', async () => {
    // Arrange
    const { trackEvent } = await import('../src/events')

    // Act: Should not throw
    expect(() => trackEvent(TEST_EVENT_NAME)).not.toThrow()
  })

  it('trackEvent emits event when SDK is initialized', async () => {
    // Arrange
    const { init } = await import('../src/init')
    const { trackEvent } = await import('../src/events')

    init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

    // Act: Should not throw
    expect(() => trackEvent(TEST_EVENT_NAME, { element: 'submit-btn' })).not.toThrow()
  })

  it('trackEvent accepts optional attributes', async () => {
    // Arrange
    const { init } = await import('../src/init')
    const { trackEvent } = await import('../src/events')

    init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

    // Act
    expect(() => trackEvent(TEST_EVENT_NAME)).not.toThrow()
    expect(() => trackEvent(TEST_EVENT_NAME, { key: 'value' })).not.toThrow()
  })
})

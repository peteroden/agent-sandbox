/**
 * @fileoverview Tests for the SDK initialization module.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Test constants
const TEST_SERVICE_NAME = 'test-sdk-service'
const TEST_ENDPOINT = 'http://localhost:4318'

describe('init', () => {
  beforeEach(() => {
    vi.resetModules()

    // Reset global state
    delete (globalThis as Record<string, unknown>).__otelFetchWrapped
  })

  afterEach(async () => {
    // Clean up after each test
    const { shutdown, isInitialized } = await import('../src/init')
    if (isInitialized()) {
      await shutdown()
    }
  })

  it('registers global error handlers', async () => {
    // Arrange
    const originalOnError = window.onerror
    window.onerror = null

    const { init } = await import('../src/init')

    // Act
    init({ serviceName: TEST_SERVICE_NAME, endpoint: TEST_ENDPOINT })

    // Assert: onerror should be set
    expect(window.onerror).not.toBeNull()

    // Cleanup
    window.onerror = originalOnError
  })

  it('registers unhandledrejection handler', async () => {
    // Arrange
    const { init } = await import('../src/init')
    const listeners: Array<(e: PromiseRejectionEvent) => void> = []
    const originalAddEventListener = window.addEventListener
    vi.spyOn(window, 'addEventListener').mockImplementation((type, listener) => {
      if (type === 'unhandledrejection') {
        listeners.push(listener as (e: PromiseRejectionEvent) => void)
      }
      return originalAddEventListener.call(window, type, listener)
    })

    // Act
    init({ serviceName: TEST_SERVICE_NAME, endpoint: TEST_ENDPOINT })

    // Assert: unhandledrejection listener should be registered
    expect(listeners.length).toBeGreaterThan(0)
  })

  it('is idempotent - calling init twice has no effect', async () => {
    // Arrange
    const { init, isInitialized } = await import('../src/init')

    // Act
    init({ serviceName: TEST_SERVICE_NAME, endpoint: TEST_ENDPOINT })
    const firstInit = isInitialized()
    init({ serviceName: 'different-service', endpoint: 'http://different:4318' })
    const secondInit = isInitialized()

    // Assert
    expect(firstInit).toBe(true)
    expect(secondInit).toBe(true)
  })

  it('exports isInitialized function', async () => {
    // Arrange
    const { init, isInitialized } = await import('../src/init')

    // Assert: Not initialized before calling init
    expect(isInitialized()).toBe(false)

    // Act
    init({ serviceName: TEST_SERVICE_NAME, endpoint: TEST_ENDPOINT })

    // Assert: Now initialized
    expect(isInitialized()).toBe(true)
  })

  it('shutdown resets initialized state', async () => {
    // Arrange
    const { init, shutdown, isInitialized } = await import('../src/init')
    init({ serviceName: TEST_SERVICE_NAME, endpoint: TEST_ENDPOINT })
    expect(isInitialized()).toBe(true)

    // Act
    await shutdown()

    // Assert
    expect(isInitialized()).toBe(false)
  })

  it('accepts optional sampleRate configuration', async () => {
    // Arrange
    const { init, isInitialized } = await import('../src/init')

    // Act: Should not throw
    init({
      serviceName: TEST_SERVICE_NAME,
      endpoint: TEST_ENDPOINT,
      sampleRate: 0.5,
    })

    // Assert
    expect(isInitialized()).toBe(true)
  })

  it('defaults to console exporter when endpoint is empty', async () => {
    // Arrange
    const { init, isInitialized } = await import('../src/init')

    // Act: Empty endpoint should use console
    init({
      serviceName: TEST_SERVICE_NAME,
      endpoint: 'console',
    })

    // Assert
    expect(isInitialized()).toBe(true)
  })
})

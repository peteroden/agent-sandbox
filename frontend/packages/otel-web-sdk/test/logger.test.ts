/**
 * @fileoverview Tests for the auto-correlating logger.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Test constants
const TEST_SERVICE_NAME = 'test-logger-service'
const TEST_LOG_MESSAGE = 'Test log message'

describe('logger', () => {
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

  it('provides debug, info, warn, error methods', async () => {
    // Arrange
    const { logger } = await import('../src/logger')

    // Assert: All methods exist
    expect(typeof logger.debug).toBe('function')
    expect(typeof logger.info).toBe('function')
    expect(typeof logger.warn).toBe('function')
    expect(typeof logger.error).toBe('function')
  })

  it('is no-op when SDK not initialized', async () => {
    // Arrange: Don't initialize SDK
    const { logger } = await import('../src/logger')

    // Act: Should not throw
    expect(() => logger.info(TEST_LOG_MESSAGE)).not.toThrow()
    expect(() => logger.debug(TEST_LOG_MESSAGE, { key: 'value' })).not.toThrow()
    expect(() => logger.warn(TEST_LOG_MESSAGE)).not.toThrow()
    expect(() => logger.error(TEST_LOG_MESSAGE)).not.toThrow()
  })

  it('emits log records when SDK is initialized', async () => {
    // Arrange
    const { init, _getLoggerProvider } = await import('../src/init')
    const { logger } = await import('../src/logger')

    init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

    // Act: Log a message
    logger.info(TEST_LOG_MESSAGE, { customAttr: 'value' })

    // Assert: Logger provider should exist
    expect(_getLoggerProvider()).not.toBeNull()
  })

  it('auto-correlates with active span context', async () => {
    // Arrange
    const { init } = await import('../src/init')
    const { logger } = await import('../src/logger')
    const { withSpan, getActiveSpan } = await import('../src/spans')

    init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

    let capturedSpan: unknown = null

    // Act: Log within a span context
    await withSpan('test-span', (_span) => {
      capturedSpan = getActiveSpan()
      logger.info(TEST_LOG_MESSAGE)
    })

    // Assert: Span should have been active
    expect(capturedSpan).not.toBeNull()
  })

  it('works gracefully when no span is active', async () => {
    // Arrange
    const { init } = await import('../src/init')
    const { logger } = await import('../src/logger')

    init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

    // Act: Log without any active span (should not throw)
    expect(() => logger.info(TEST_LOG_MESSAGE)).not.toThrow()
  })

  it('accepts optional attributes', async () => {
    // Arrange
    const { init } = await import('../src/init')
    const { logger } = await import('../src/logger')

    init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

    // Act: Log with various attribute types
    expect(() => logger.info(TEST_LOG_MESSAGE, {
      stringAttr: 'value',
      numberAttr: 42,
      boolAttr: true,
    })).not.toThrow()
  })

  it('handles null and undefined attributes gracefully', async () => {
    // Arrange
    const { init } = await import('../src/init')
    const { logger } = await import('../src/logger')

    init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

    // Act: Log with undefined attributes
    expect(() => logger.info(TEST_LOG_MESSAGE, undefined)).not.toThrow()
  })

  it('accepts explicit span for correlation', async () => {
    // Arrange
    const { init } = await import('../src/init')
    const { logger } = await import('../src/logger')
    const { startSpan } = await import('../src/spans')

    init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

    const span = startSpan('explicit-span')

    // Act: Log with explicit span (should not throw)
    expect(() => logger.info(TEST_LOG_MESSAGE, { key: 'value' }, span)).not.toThrow()

    // Cleanup
    span.end()
  })
})

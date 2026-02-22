/**
 * @fileoverview Tests for span management utilities.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Test constants
const TEST_SERVICE_NAME = 'test-spans-service'
const TEST_SPAN_NAME = 'test-operation'

describe('spans', () => {
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

  describe('startSpan', () => {
    it('creates a span with the given name', async () => {
      // Arrange
      const { init } = await import('../src/init')
      const { startSpan } = await import('../src/spans')

      init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

      // Act
      const span = startSpan(TEST_SPAN_NAME)

      // Assert
      expect(span).toBeDefined()
      expect(span.isRecording()).toBe(true)

      // Cleanup
      span.end()
    })

    it('accepts span options', async () => {
      // Arrange
      const { init } = await import('../src/init')
      const { startSpan } = await import('../src/spans')

      init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

      // Act
      const span = startSpan(TEST_SPAN_NAME, {
        attributes: { 'custom.attr': 'value' },
      })

      // Assert
      expect(span).toBeDefined()

      // Cleanup
      span.end()
    })
  })

  describe('getActiveSpan', () => {
    it('returns undefined when no span is active', async () => {
      // Arrange
      const { init } = await import('../src/init')
      const { getActiveSpan } = await import('../src/spans')

      init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

      // Act
      const span = getActiveSpan()

      // Assert
      expect(span).toBeUndefined()
    })

    it('returns the active span within withSpan callback', async () => {
      // Arrange
      const { init } = await import('../src/init')
      const { withSpan, getActiveSpan } = await import('../src/spans')

      init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

      // Act
      let capturedSpan: unknown = null
      await withSpan(TEST_SPAN_NAME, () => {
        capturedSpan = getActiveSpan()
      })

      // Assert
      expect(capturedSpan).not.toBeUndefined()
    })
  })

  describe('withSpan', () => {
    it('executes the function within span context', async () => {
      // Arrange
      const { init } = await import('../src/init')
      const { withSpan } = await import('../src/spans')

      init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

      // Act
      let executed = false
      await withSpan(TEST_SPAN_NAME, () => {
        executed = true
      })

      // Assert
      expect(executed).toBe(true)
    })

    it('returns the result of the function', async () => {
      // Arrange
      const { init } = await import('../src/init')
      const { withSpan } = await import('../src/spans')

      init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

      // Act
      const result = await withSpan(TEST_SPAN_NAME, () => {
        return 42
      })

      // Assert
      expect(result).toBe(42)
    })

    it('handles async functions', async () => {
      // Arrange
      const { init } = await import('../src/init')
      const { withSpan } = await import('../src/spans')

      init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

      // Act
      const result = await withSpan(TEST_SPAN_NAME, async () => {
        await new Promise((resolve) => setTimeout(resolve, 10))
        return 'async result'
      })

      // Assert
      expect(result).toBe('async result')
    })

    it('records exceptions and rethrows', async () => {
      // Arrange
      const { init } = await import('../src/init')
      const { withSpan } = await import('../src/spans')

      init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

      const testError = new Error('Test error')

      // Act & Assert
      await expect(
        withSpan(TEST_SPAN_NAME, () => {
          throw testError
        })
      ).rejects.toThrow('Test error')
    })

    it('passes the span to the callback', async () => {
      // Arrange
      const { init } = await import('../src/init')
      const { withSpan } = await import('../src/spans')

      init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

      // Act
      let receivedSpan: unknown = null
      await withSpan(TEST_SPAN_NAME, (span) => {
        receivedSpan = span
      })

      // Assert
      expect(receivedSpan).not.toBeNull()
    })
  })

  describe('addSpanEvent', () => {
    it('does nothing when no span is active', async () => {
      // Arrange
      const { init } = await import('../src/init')
      const { addSpanEvent } = await import('../src/spans')

      init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

      // Act: Should not throw
      expect(() => addSpanEvent('test-event')).not.toThrow()
    })

    it('adds event to active span', async () => {
      // Arrange
      const { init } = await import('../src/init')
      const { withSpan, addSpanEvent } = await import('../src/spans')

      init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

      // Act: Should not throw
      await withSpan(TEST_SPAN_NAME, () => {
        expect(() => addSpanEvent('test-event', { key: 'value' })).not.toThrow()
      })
    })
  })
})

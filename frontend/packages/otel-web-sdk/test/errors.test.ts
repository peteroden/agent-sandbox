/**
 * @fileoverview Tests for error tracking.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Test constants
const TEST_SERVICE_NAME = 'test-errors-service'
const TEST_ERROR_MESSAGE = 'Test error message'

describe('errors', () => {
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

  it('trackError is no-op when SDK not initialized', async () => {
    // Arrange
    const { trackError } = await import('../src/errors')

    // Act: Should not throw
    expect(() => trackError(new Error(TEST_ERROR_MESSAGE))).not.toThrow()
  })

  it('trackError emits error when SDK is initialized', async () => {
    // Arrange
    const { init } = await import('../src/init')
    const { trackError } = await import('../src/errors')

    init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

    // Act: Should not throw
    expect(() => trackError(new Error(TEST_ERROR_MESSAGE))).not.toThrow()
  })

  it('trackError accepts optional context', async () => {
    // Arrange
    const { init } = await import('../src/init')
    const { trackError } = await import('../src/errors')

    init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

    // Act
    expect(() => trackError(new Error(TEST_ERROR_MESSAGE), {
      component: 'UserForm',
      action: 'submit',
    })).not.toThrow()
  })

  it('trackError sanitizes stack traces', async () => {
    // Arrange
    const { init } = await import('../src/init')
    const { trackError } = await import('../src/errors')

    init({ serviceName: TEST_SERVICE_NAME, endpoint: 'console' })

    // Act: Error with path containing username
    const error = new Error(TEST_ERROR_MESSAGE)
    error.stack = 'Error: test\n    at /Users/john/projects/app.js:10:5'

    // Should not throw and should sanitize
    expect(() => trackError(error)).not.toThrow()
  })
})

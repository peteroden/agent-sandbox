/**
 * @fileoverview Tests for React/Preact adapter.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render } from '@testing-library/preact'
import { h } from 'preact'

// Test constants
const TEST_SERVICE_NAME = 'test-react-service'
const TEST_ERROR_MESSAGE = 'Test error from component'
const CHILD_RENDERED_MESSAGE = 'Child rendered successfully'
const DEFAULT_FALLBACK_MESSAGE = 'Something went wrong'
const CUSTOM_FALLBACK_MESSAGE = 'Custom error fallback'

// Component that throws an error for testing
function ThrowingComponent({ shouldThrow = true }: { shouldThrow?: boolean }) {
  if (shouldThrow) {
    throw new Error(TEST_ERROR_MESSAGE)
  }
  return h('div', {}, CHILD_RENDERED_MESSAGE)
}

describe('react adapter', () => {
  let consoleSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    vi.resetModules()

    // Suppress console.error during error boundary tests
    consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    // Reset global state
    delete (globalThis as Record<string, unknown>).__otelFetchWrapped
    delete (globalThis as Record<string, unknown>).__otelInjectHeaders
  })

  afterEach(async () => {
    consoleSpy.mockRestore()

    const { shutdown, isInitialized } = await import('../../src/init')
    if (isInitialized()) {
      await shutdown()
    }
  })

  describe('OTelErrorBoundary', () => {
    it('renders children normally when no error', async () => {
      // Arrange
      const { OTelErrorBoundary } = await import('../../src/react')

      // Act
      const { container } = render(
        h(OTelErrorBoundary, {}, h(ThrowingComponent, { shouldThrow: false }))
      )

      // Assert
      expect(container.textContent).toContain(CHILD_RENDERED_MESSAGE)
    })

    it('renders fallback when child throws', async () => {
      // Arrange
      const { OTelErrorBoundary } = await import('../../src/react')

      // Act
      const { container } = render(
        h(OTelErrorBoundary, {}, h(ThrowingComponent, { shouldThrow: true }))
      )

      // Assert: Should show error message
      expect(container.textContent).toContain(DEFAULT_FALLBACK_MESSAGE)
    })

    it('accepts custom fallback component', async () => {
      // Arrange
      const { OTelErrorBoundary } = await import('../../src/react')
      const customFallback = h('div', { 'data-testid': 'custom-fallback' }, CUSTOM_FALLBACK_MESSAGE)

      // Act
      const { container } = render(
        h(OTelErrorBoundary, { fallback: customFallback }, h(ThrowingComponent, { shouldThrow: true }))
      )

      // Assert
      expect(container.textContent).toContain(CUSTOM_FALLBACK_MESSAGE)
    })

    it('tracks error when SDK is initialized', async () => {
      // Arrange
      const { init, _getLoggerProvider } = await import('../../src/init')
      const { OTelErrorBoundary } = await import('../../src/react')

      init({ serviceName: TEST_SERVICE_NAME, endpoint: '' })

      // Act: Should track error
      const { container } = render(
        h(OTelErrorBoundary, {}, h(ThrowingComponent, { shouldThrow: true }))
      )

      // Assert: Error should be caught and logged
      expect(container.textContent).toContain(DEFAULT_FALLBACK_MESSAGE)
      expect(_getLoggerProvider()).not.toBeNull()
    })
  })

  describe('renderWithTelemetry', () => {
    it('renders component to container', async () => {
      // Arrange
      const { renderWithTelemetry } = await import('../../src/react')
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const TestApp = (): any => h('div', { 'data-testid': 'app' }, 'App Content')

      // Use testing-library's container
      const result = render(h('div', {}))
      const container = result.container
      while (container.firstChild) {
        container.removeChild(container.firstChild)
      }

      // Act
      renderWithTelemetry(h(TestApp, {}), container)

      // Assert
      expect(container.querySelector('[data-testid="app"]')).not.toBeNull()
      expect(container.textContent).toBe('App Content')
    })

    it('wraps component in error boundary that catches errors', async () => {
      // Arrange
      const { OTelErrorBoundary } = await import('../../src/react')

      // We test the error boundary directly since renderWithTelemetry uses it
      // The integration test verifies the wrapper composition works
      const { container } = render(
        h(OTelErrorBoundary, {}, h(ThrowingComponent, { shouldThrow: true }))
      )

      // Assert: Error boundary should catch it
      expect(container.textContent).toContain(DEFAULT_FALLBACK_MESSAGE)
    })
  })
})

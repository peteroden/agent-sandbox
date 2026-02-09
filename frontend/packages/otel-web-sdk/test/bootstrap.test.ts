/**
 * @fileoverview Tests for the bootstrap fetch trap.
 *
 * These tests verify that the bootstrap script properly marks fetch
 * so OpenTelemetry auto-instrumentation can wrap it, even if libraries
 * cache a reference early.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Test constants
const TEST_URL = 'http://localhost:8888/api/test'

describe('fetch trap', () => {
  let originalFetch: typeof globalThis.fetch
  let originalDefineProperty: typeof Object.defineProperty

  beforeEach(() => {
    // Store originals
    originalFetch = globalThis.fetch
    originalDefineProperty = Object.defineProperty

    // Reset global state
    delete (globalThis as Record<string, unknown>).__otelFetchWrapped

    // Reset module cache to force fresh imports
    vi.resetModules()
  })

  afterEach(() => {
    // Restore originals
    globalThis.fetch = originalFetch
    Object.defineProperty = originalDefineProperty
  })

  it('marks fetch before any module code runs', async () => {
    // Arrange: Set up a mock fetch
    const mockFetch = vi.fn().mockResolvedValue(new Response('ok'))
    globalThis.fetch = mockFetch

    // Act: Load the bootstrap trap
    await import('../src/bootstrap')

    // Assert: fetch should now be marked
    expect((globalThis.fetch as { __otelWrapped?: boolean }).__otelWrapped).toBe(true)
  })

  it('marks fetch when polyfill assigns new implementation', async () => {
    // Arrange: Load bootstrap first
    await import('../src/bootstrap')

    // Act: Simulate a polyfill reassigning fetch
    const polyfillFetch = vi.fn().mockResolvedValue(new Response('polyfill'))
    globalThis.fetch = polyfillFetch

    // Assert: The new fetch should also be marked
    expect((globalThis.fetch as { __otelWrapped?: boolean }).__otelWrapped).toBe(true)
  })

  it('handles fetch not existing initially then being assigned', async () => {
    // Arrange: Remove fetch temporarily
    delete (globalThis as Record<string, unknown>).fetch
    delete (globalThis as Record<string, unknown>).__otelFetchWrapped

    // Act: Load bootstrap (should not throw)
    await import('../src/bootstrap')

    // Assert: Trap should be set up
    expect((globalThis as { __otelFetchWrapped?: boolean }).__otelFetchWrapped).toBe(true)

    // Assign fetch after trap is set - should mark
    const mockFetch = vi.fn().mockResolvedValue(new Response('ok'))
    globalThis.fetch = mockFetch
    expect((globalThis.fetch as { __otelWrapped?: boolean }).__otelWrapped).toBe(true)
  })

  it('preserves original fetch functionality', async () => {
    // Arrange
    const responseBody = { data: 'test' }
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )
    globalThis.fetch = mockFetch

    // Load bootstrap
    await import('../src/bootstrap')

    // Act
    const response = await globalThis.fetch(TEST_URL)
    const json = await response.json()

    // Assert
    expect(mockFetch).toHaveBeenCalledTimes(1)
    expect(json).toEqual(responseBody)
  })

  it('does not double-mark already marked fetch', async () => {
    // Arrange: Load bootstrap twice (simulating duplicate script tags)
    await import('../src/bootstrap')
    const firstFetch = globalThis.fetch

    // Clear the module cache to force re-evaluation
    vi.resetModules()
    await import('../src/bootstrap')

    // Assert: Should be the same fetch (not double-marked)
    expect(globalThis.fetch).toBe(firstFetch)
  })
})

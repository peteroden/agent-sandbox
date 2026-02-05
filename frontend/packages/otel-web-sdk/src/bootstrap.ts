/**
 * @fileoverview Bootstrap script for fetch trap.
 *
 * This script MUST run before any other JavaScript to ensure we can
 * intercept fetch before third-party libraries cache a reference.
 *
 * Note: Header injection is handled by OpenTelemetry auto-instrumentation.
 * This bootstrap only sets up a property trap so auto-instrumentation
 * can wrap fetch even if libraries cache fetch early.
 *
 * @example
 * // In HTML, include as first script:
 * <script src="./bootstrap.iife.js"></script>
 */
/// <reference path="./global.d.ts" />

type FetchFunction = typeof globalThis.fetch & { __otelWrapped?: boolean }

/**
 * Mark a fetch function as wrapped (for detection purposes only).
 */
function markFetch(fn: typeof globalThis.fetch): FetchFunction {
  if (!fn || (fn as FetchFunction).__otelWrapped) {
    return fn as FetchFunction
  }
  // Store reference for debugging
  globalThis.__otelUnwrappedFetch = fn
  // Mark but don't actually wrap - let auto-instrumentation do the real work
  ;(fn as FetchFunction).__otelWrapped = true
  return fn as FetchFunction
}

/**
 * Set up property trap on globalThis.fetch.
 *
 * This ensures any future fetch assignments (polyfills, lazy loading)
 * are also captured by OpenTelemetry instrumentation.
 */
function setupFetchTrap(): void {
  if (globalThis.__otelFetchWrapped) {
    return
  }

  let _fetch: FetchFunction | undefined = globalThis.fetch as FetchFunction | undefined

  Object.defineProperty(globalThis, 'fetch', {
    get(): FetchFunction | undefined {
      return _fetch
    },
    set(fn: FetchFunction | undefined) {
      _fetch = fn ? markFetch(fn) : fn
    },
    configurable: true,
    enumerable: true,
  })

  globalThis.__otelFetchWrapped = true

  // Mark current fetch if it exists
  if (_fetch) {
    globalThis.fetch = _fetch
  }
}

// Run immediately
setupFetchTrap()

export { markFetch, setupFetchTrap }

/**
 * @fileoverview Global type declarations for otel-web-sdk.
 */

declare global {
  /**
   * Global fetch interception state.
   */
  interface Window {
    /** Flag indicating fetch trap has been set up */
    __otelFetchWrapped?: boolean
    /** Callback to inject trace headers into fetch requests */
    __otelInjectHeaders?: (headers: Headers) => void
    /** Reference to the original unwrapped fetch (for testing) */
    __otelUnwrappedFetch?: typeof globalThis.fetch
  }

  // Also extend var for Node.js/globalThis compatibility
  // eslint-disable-next-line no-var
  var __otelFetchWrapped: boolean | undefined
  // eslint-disable-next-line no-var
  var __otelInjectHeaders: ((headers: Headers) => void) | undefined
  // eslint-disable-next-line no-var
  var __otelUnwrappedFetch: typeof globalThis.fetch | undefined

  /** Package name injected by Vite at build time */
  const __PKG_NAME__: string
  /** Package version injected by Vite at build time */
  const __PKG_VERSION__: string
}

export {}

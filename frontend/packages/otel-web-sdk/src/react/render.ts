/**
 * @fileoverview Render helper with automatic error boundary.
 */
import { render, type VNode, h } from 'preact'
import { OTelErrorBoundary } from './error-boundary'

/**
 * Render a component with automatic telemetry error tracking.
 *
 * Wraps the component in an OTelErrorBoundary for zero-code error handling.
 *
 * @param vnode - The component to render
 * @param container - The DOM container to render into
 *
 * @example
 * ```ts
 * import { init } from '@agent-sandbox/otel-web-sdk'
 * import { renderWithTelemetry } from '@agent-sandbox/otel-web-sdk/react'
 *
 * init({ serviceName: 'my-app', endpoint: 'http://localhost:4318' })
 * renderWithTelemetry(<App />, document.getElementById('root')!)
 * ```
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function renderWithTelemetry(vnode: VNode<any>, container: Element): void {
  render(
    h(OTelErrorBoundary, null, vnode),
    container
  )
}

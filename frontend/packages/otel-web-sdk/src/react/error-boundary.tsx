/**
 * @fileoverview Error boundary component for React/Preact.
 */
import { Component, type VNode, h, type ComponentChildren } from 'preact'
import { trackError } from '../errors'
import { sanitizePath } from '../init'

export interface ErrorBoundaryProps {
  /** Custom fallback UI to show on error */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  fallback?: VNode<any>
  /** Children to render */
  children?: ComponentChildren
}

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
}

/**
 * Error boundary that automatically tracks errors to telemetry.
 *
 * Catches render errors in child components and displays a fallback UI.
 *
 * @example
 * ```tsx
 * <OTelErrorBoundary fallback={<ErrorPage />}>
 *   <App />
 * </OTelErrorBoundary>
 * ```
 */
export class OTelErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: { componentStack?: string }): void {
    // Sanitize component stack for PII
    const sanitizedStack = sanitizePath(errorInfo.componentStack)

    // Track to telemetry
    trackError(error, {
      'error.boundary': 'true',
      'error.component_stack': sanitizedStack,
    })
  }

  render(): ComponentChildren {
    if (this.state.hasError) {
      // Render custom fallback or default
      if (this.props.fallback) {
        return this.props.fallback
      }

      return h(
        'div',
        {
          style: {
            padding: '20px',
            textAlign: 'center',
            fontFamily: 'system-ui, sans-serif',
          },
        },
        h('h2', null, 'Something went wrong'),
        h(
          'p',
          { style: { color: '#666' } },
          'An error occurred while rendering this component.'
        )
      )
    }

    return this.props.children ?? null
  }
}

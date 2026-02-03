import { Component, type ComponentChildren, type VNode } from 'preact';
import { logger, sanitizePath } from '../services/telemetry';

interface OTelErrorBoundaryProps {
  children: ComponentChildren;
  fallback?: VNode;
}

interface OTelErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error boundary component that catches React/Preact errors and logs them via OTel.
 *
 * Uses Preact class component since functional components cannot implement componentDidCatch.
 */
export class OTelErrorBoundary extends Component<OTelErrorBoundaryProps, OTelErrorBoundaryState> {
  constructor(props: OTelErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): Partial<OTelErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: { componentStack?: string }): void {
    // Log structured error with OTel
    logger.error('React error boundary caught error', {
      'error.message': error.message,
      'error.type': error.name,
      'error.stack': sanitizePath(error.stack),
      'error.component_stack': sanitizePath(errorInfo.componentStack),
    });
  }

  render(): ComponentChildren {
    if (this.state.hasError) {
      // Render custom fallback if provided, otherwise default
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg">
            <div className="mb-4 flex items-center justify-center">
              <svg
                className="h-12 w-12 text-red-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <h2 className="mb-2 text-center text-xl font-semibold text-gray-800">
              Something went wrong
            </h2>
            <p className="mb-4 text-center text-gray-600">
              An unexpected error occurred. Please refresh the page to try again.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="w-full rounded-lg bg-blue-500 px-4 py-2 font-medium text-white hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Refresh Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

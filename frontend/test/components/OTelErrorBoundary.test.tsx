import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/preact';
import { OTelErrorBoundary } from '../../src/components/OTelErrorBoundary.tsx';
import * as telemetry from '../../src/services/telemetry';

// Component that throws an error for testing
function ThrowingComponent({ shouldThrow = true }: { shouldThrow?: boolean }) {
  if (shouldThrow) {
    throw new Error('Test error from component');
  }
  return <div>Child rendered successfully</div>;
}

describe('OTelErrorBoundary', () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;
  let loggerErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // Suppress console.error during error boundary tests
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    loggerErrorSpy = vi.spyOn(telemetry.logger, 'error');
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    loggerErrorSpy.mockRestore();
  });

  it('renders children normally when no error occurs', () => {
    const { container } = render(
      <OTelErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </OTelErrorBoundary>
    );

    expect(container.textContent).toContain('Child rendered successfully');
  });

  it('renders fallback UI when error occurs', () => {
    const { container } = render(
      <OTelErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </OTelErrorBoundary>
    );

    expect(container.textContent).toContain('Something went wrong');
  });

  it('calls logger.error with error details when error occurs', () => {
    render(
      <OTelErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </OTelErrorBoundary>
    );

    expect(loggerErrorSpy).toHaveBeenCalledWith(
      'React error boundary caught error',
      expect.objectContaining({
        'error.message': 'Test error from component',
        'error.type': 'Error',
      })
    );
  });

  it('renders custom fallback when provided', () => {
    const customFallback = <div>Custom error fallback</div>;

    const { container } = render(
      <OTelErrorBoundary fallback={customFallback}>
        <ThrowingComponent shouldThrow={true} />
      </OTelErrorBoundary>
    );

    expect(container.textContent).toContain('Custom error fallback');
  });

  it('includes sanitized component stack in error attributes', () => {
    render(
      <OTelErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </OTelErrorBoundary>
    );

    expect(loggerErrorSpy).toHaveBeenCalledWith(
      'React error boundary caught error',
      expect.objectContaining({
        'error.component_stack': expect.any(String),
      })
    );

    // Verify no PII in stack (no /Users/username/ paths)
    const callArgs = loggerErrorSpy.mock.calls[0]?.[1];
    const stackValue = callArgs?.['error.component_stack'];
    if (typeof stackValue === 'string') {
      expect(stackValue).not.toMatch(/\/Users\/[a-zA-Z0-9_-]+\//);
    }
  });
});

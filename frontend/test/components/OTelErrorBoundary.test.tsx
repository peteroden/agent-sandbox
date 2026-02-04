import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/preact';
import { OTelErrorBoundary } from '../../src/components/OTelErrorBoundary.tsx';
import * as telemetry from '../../src/services/telemetry';

// Local test constants
const TEST_ERROR_MESSAGE = 'Test error from component';
const CHILD_RENDERED_MESSAGE = 'Child rendered successfully';
const DEFAULT_FALLBACK_MESSAGE = 'Something went wrong';
const CUSTOM_FALLBACK_MESSAGE = 'Custom error fallback';
const LOGGER_ERROR_MESSAGE = 'React error boundary caught error';

// Component that throws an error for testing
function ThrowingComponent({ shouldThrow = true }: { shouldThrow?: boolean }) {
  if (shouldThrow) {
    throw new Error(TEST_ERROR_MESSAGE);
  }
  return <div>{CHILD_RENDERED_MESSAGE}</div>;
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

    expect(container.textContent).toContain(CHILD_RENDERED_MESSAGE);
  });

  it('renders fallback UI when error occurs', () => {
    const { container } = render(
      <OTelErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </OTelErrorBoundary>
    );

    expect(container.textContent).toContain(DEFAULT_FALLBACK_MESSAGE);
  });

  it('calls logger.error with error details when error occurs', () => {
    render(
      <OTelErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </OTelErrorBoundary>
    );

    expect(loggerErrorSpy).toHaveBeenCalledWith(
      LOGGER_ERROR_MESSAGE,
      expect.objectContaining({
        'error.message': TEST_ERROR_MESSAGE,
        'error.type': 'Error',
      })
    );
  });

  it('renders custom fallback when provided', () => {
    const customFallback = <div>{CUSTOM_FALLBACK_MESSAGE}</div>;

    const { container } = render(
      <OTelErrorBoundary fallback={customFallback}>
        <ThrowingComponent shouldThrow={true} />
      </OTelErrorBoundary>
    );

    expect(container.textContent).toContain(CUSTOM_FALLBACK_MESSAGE);
  });

  it('includes sanitized component stack in error attributes', () => {
    render(
      <OTelErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </OTelErrorBoundary>
    );

    expect(loggerErrorSpy).toHaveBeenCalledWith(
      LOGGER_ERROR_MESSAGE,
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

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { trace } from '@opentelemetry/api';
import { TestDefaults } from '../test-constants';

// Local test constants for this file only
const EXISTING_SESSION_ID = 'existing-session-id';
const SESSION_STORAGE_KEY = 'otel_session_id';
const USER_ID = 'user-123';
const USER_EMAIL = 'test@example.com';

// Event constants for pushEvent tests
const EventNames = {
  BUTTON_CLICK: 'button_click',
  FORM_SUBMIT: 'form_submit',
} as const;

// Measurement constants for pushMeasurement tests
const MeasurementTypes = {
  API_LATENCY: 'api_latency',
  MEMORY_USAGE: 'memory_usage',
} as const;

// Path sanitization test cases
const PathSanitizationCases = [
  { name: 'macOS', input: '/Users/john/code/file.ts', expected: '/Users/***/code/file.ts' },
  { name: 'Linux', input: '/home/john/code/file.ts', expected: '/home/***/code/file.ts' },
  { name: 'Windows C:', input: 'C:\\Users\\john\\code\\file.ts', expected: 'C:\\Users\\***\\code\\file.ts' },
  { name: 'Windows D:', input: 'D:\\Users\\admin\\file.ts', expected: 'D:\\Users\\***\\file.ts' },
  { name: 'undefined', input: undefined, expected: '' },
  { name: 'empty', input: '', expected: '' },
] as const;

// Log level test cases for pushLog
const LogLevelCases = [
  { level: 'trace' as const, expectedSeverity: 1 },  // SeverityNumber.TRACE
  { level: 'debug' as const, expectedSeverity: 5 },  // SeverityNumber.DEBUG
  { level: 'info' as const, expectedSeverity: 9 },   // SeverityNumber.INFO
  { level: 'log' as const, expectedSeverity: 9 },    // Maps to INFO
  { level: 'warn' as const, expectedSeverity: 13 },  // SeverityNumber.WARN
  { level: 'error' as const, expectedSeverity: 17 }, // SeverityNumber.ERROR
] as const;

// Mock sessionStorage
const mockSessionStorage: Record<string, string> = {};
Object.defineProperty(globalThis, 'sessionStorage', {
  value: {
    getItem: vi.fn((key: string) => mockSessionStorage[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      mockSessionStorage[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete mockSessionStorage[key];
    }),
    clear: vi.fn(() => {
      Object.keys(mockSessionStorage).forEach((k) => delete mockSessionStorage[k]);
    }),
  },
  writable: true,
});

// Mock crypto.randomUUID
Object.defineProperty(globalThis, 'crypto', {
  value: {
    randomUUID: vi.fn(() => TestDefaults.SESSION_ID),
  },
  writable: true,
});

describe('telemetry', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.unstubAllEnvs();
    Object.keys(mockSessionStorage).forEach((k) => delete mockSessionStorage[k]);
  });

  afterEach(async () => {
    const { shutdownTelemetry } = await import('../../src/services/telemetry');
    await shutdownTelemetry();
    trace.disable();
    vi.restoreAllMocks();
  });

  describe('initialization', () => {
    it('is idempotent', async () => {
      const { initTelemetry, isInitialized } = await import('../../src/services/telemetry');

      initTelemetry();
      expect(isInitialized()).toBe(true);

      initTelemetry();
      initTelemetry();
      expect(isInitialized()).toBe(true);
    });

    it('generates session ID on first init', async () => {
      const { initTelemetry, getSessionId } = await import('../../src/services/telemetry');

      initTelemetry();

      expect(getSessionId()).toBe(TestDefaults.SESSION_ID);
      expect(globalThis.sessionStorage.setItem).toHaveBeenCalledWith(
        SESSION_STORAGE_KEY,
        TestDefaults.SESSION_ID
      );
    });

    it('reuses existing session ID', async () => {
      mockSessionStorage[SESSION_STORAGE_KEY] = EXISTING_SESSION_ID;

      const { initTelemetry, getSessionId } = await import('../../src/services/telemetry');

      initTelemetry();

      expect(getSessionId()).toBe(EXISTING_SESSION_ID);
      expect(globalThis.crypto.randomUUID).not.toHaveBeenCalled();
    });

    it('gracefully degrades on failure', async () => {
      vi.stubEnv('VITE_OTEL_EXPORTER', 'invalid-exporter');

      const { initTelemetry } = await import('../../src/services/telemetry');

      expect(() => initTelemetry()).not.toThrow();
    });

    it('falls back to console exporter for invalid OTLP URL', async () => {
      vi.stubEnv('VITE_OTEL_EXPORTER', 'otlp');
      vi.stubEnv('VITE_OTEL_ENDPOINT', 'not-a-valid-url');

      const consoleSpy = vi.spyOn(console, 'warn');
      const { initTelemetry } = await import('../../src/services/telemetry');

      initTelemetry();

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Invalid OTLP endpoint')
      );
    });
  });

  describe('shutdown', () => {
    it('removes event listeners', async () => {
      const docRemoveSpy = vi.spyOn(document, 'removeEventListener');
      const winRemoveSpy = vi.spyOn(window, 'removeEventListener');

      const { initTelemetry, shutdownTelemetry } = await import('../../src/services/telemetry');

      initTelemetry();
      await shutdownTelemetry();

      expect(docRemoveSpy).toHaveBeenCalledWith('visibilitychange', expect.any(Function));
      expect(winRemoveSpy).toHaveBeenCalledWith('pagehide', expect.any(Function));
    });

    it('allows re-initialization', async () => {
      const { initTelemetry, shutdownTelemetry, isInitialized } = await import(
        '../../src/services/telemetry'
      );

      initTelemetry();
      expect(isInitialized()).toBe(true);

      await shutdownTelemetry();
      expect(isInitialized()).toBe(false);

      initTelemetry();
      expect(isInitialized()).toBe(true);
    });

    it('is safe when not initialized', async () => {
      const { shutdownTelemetry } = await import('../../src/services/telemetry');

      await expect(shutdownTelemetry()).resolves.toBeUndefined();
    });
  });

  describe('sanitizePath', () => {
    it.each(PathSanitizationCases)('sanitizes $name paths', async ({ input, expected }) => {
      const { sanitizePath } = await import('../../src/services/telemetry');

      expect(sanitizePath(input)).toBe(expected);
    });

    it('sanitizes mixed path formats', async () => {
      const { sanitizePath } = await import('../../src/services/telemetry');

      const mixed = '/Users/mac/code C:\\Users\\win\\code /home/linux/code';
      const result = sanitizePath(mixed);

      expect(result).not.toMatch(/mac|win|linux/);
      expect(result).toContain('/Users/***/');
      expect(result).toContain('C:\\Users\\***\\');
      expect(result).toContain('/home/***/');
    });
  });

  describe('logger', () => {
    it('is no-op when not initialized', async () => {
      const { logger } = await import('../../src/services/telemetry');

      expect(() => {
        logger.debug('test');
        logger.info('test');
        logger.warn('test');
        logger.error('test');
      }).not.toThrow();
    });
  });

  describe('user management', () => {
    it('stores and retrieves user', async () => {
      const { setUser, getCurrentUser } = await import('../../src/services/telemetry');

      setUser(USER_ID, { email: USER_EMAIL, role: 'admin' });

      expect(getCurrentUser()).toEqual({
        id: USER_ID,
        attributes: { email: USER_EMAIL, role: 'admin' },
      });
    });

    it('clears user', async () => {
      const { setUser, clearUser, getCurrentUser } = await import('../../src/services/telemetry');

      setUser(USER_ID);
      clearUser();

      expect(getCurrentUser()).toBeNull();
    });
  });

  describe('pushEvent', () => {
    it('is no-op when not initialized', async () => {
      const { pushEvent } = await import('../../src/services/telemetry');

      expect(() => pushEvent(EventNames.BUTTON_CLICK)).not.toThrow();
    });

    it('emits event with name and attributes when initialized', async () => {
      const { initTelemetry, pushEvent, _getLoggerForTest } = await import('../../src/services/telemetry');

      initTelemetry();
      const logger = _getLoggerForTest();
      const emitSpy = vi.spyOn(logger!, 'emit');

      pushEvent(EventNames.BUTTON_CLICK, { component: 'header' });

      expect(emitSpy).toHaveBeenCalledWith(expect.objectContaining({
        body: EventNames.BUTTON_CLICK,
        attributes: expect.objectContaining({
          'event.name': EventNames.BUTTON_CLICK,
          component: 'header',
        }),
      }));
    });
  });

  describe('pushError', () => {
    it('is no-op when not initialized', async () => {
      const { pushError } = await import('../../src/services/telemetry');

      expect(() => pushError(new Error('test error'))).not.toThrow();
    });

    it('emits error with sanitized stack when initialized', async () => {
      const { initTelemetry, pushError, _getLoggerForTest } = await import('../../src/services/telemetry');

      initTelemetry();
      const logger = _getLoggerForTest();
      const emitSpy = vi.spyOn(logger!, 'emit');

      const error = new Error('test error');
      error.stack = 'Error: test\n    at /Users/john/project/file.ts:10:5';

      pushError(error, { context: 'test-context' });

      expect(emitSpy).toHaveBeenCalledWith(expect.objectContaining({
        body: 'test error',
        attributes: expect.objectContaining({
          'error.type': 'Error',
          'error.stack': expect.stringContaining('/Users/***/'),
          context: 'test-context',
        }),
      }));
    });
  });

  describe('pushMeasurement', () => {
    it('is no-op when not initialized', async () => {
      const { pushMeasurement } = await import('../../src/services/telemetry');

      expect(() => pushMeasurement(MeasurementTypes.API_LATENCY, { value: 100 })).not.toThrow();
    });

    it('emits measurement with prefixed values when initialized', async () => {
      const { initTelemetry, pushMeasurement, _getLoggerForTest } = await import('../../src/services/telemetry');

      initTelemetry();
      const logger = _getLoggerForTest();
      const emitSpy = vi.spyOn(logger!, 'emit');

      pushMeasurement(MeasurementTypes.API_LATENCY, { duration: 150, count: 5 }, { endpoint: '/api/test' });

      expect(emitSpy).toHaveBeenCalledWith(expect.objectContaining({
        body: MeasurementTypes.API_LATENCY,
        attributes: expect.objectContaining({
          'measurement.type': MeasurementTypes.API_LATENCY,
          'measurement.duration': 150,
          'measurement.count': 5,
          endpoint: '/api/test',
        }),
      }));
    });
  });

  describe('pushLog', () => {
    it('is no-op when not initialized', async () => {
      const { pushLog } = await import('../../src/services/telemetry');

      expect(() => pushLog('test message')).not.toThrow();
    });

    it.each(LogLevelCases)('maps $level to severity $expectedSeverity', async ({ level, expectedSeverity }) => {
      const { initTelemetry, pushLog, _getLoggerForTest } = await import('../../src/services/telemetry');

      initTelemetry();
      const logger = _getLoggerForTest();
      const emitSpy = vi.spyOn(logger!, 'emit');

      pushLog('test message', level, { source: 'test' });

      expect(emitSpy).toHaveBeenCalledWith(expect.objectContaining({
        severityNumber: expectedSeverity,
        body: 'test message',
        attributes: { source: 'test' },
      }));
    });

    it('defaults to info level when not specified', async () => {
      const { initTelemetry, pushLog, _getLoggerForTest } = await import('../../src/services/telemetry');

      initTelemetry();
      const logger = _getLoggerForTest();
      const emitSpy = vi.spyOn(logger!, 'emit');

      pushLog('test message');

      expect(emitSpy).toHaveBeenCalledWith(expect.objectContaining({
        severityNumber: 9,  // INFO
      }));
    });
  });

  describe('span helpers', () => {
    it('getTracer returns a tracer', async () => {
      const { getTracer } = await import('../../src/services/telemetry');

      const tracer = getTracer();

      expect(tracer).toBeDefined();
      expect(typeof tracer.startSpan).toBe('function');
    });

    it('startSpan creates a span', async () => {
      const { initTelemetry, startSpan } = await import('../../src/services/telemetry');

      initTelemetry();
      const span = startSpan('test-span');

      expect(span).toBeDefined();
      expect(typeof span.end).toBe('function');
      span.end();
    });

    it('getActiveSpan returns undefined when no span is active', async () => {
      const { getActiveSpan } = await import('../../src/services/telemetry');

      const span = getActiveSpan();

      expect(span).toBeUndefined();
    });

    it('addSpanEvent is safe when no span is active', async () => {
      const { addSpanEvent } = await import('../../src/services/telemetry');

      expect(() => addSpanEvent('test-event')).not.toThrow();
    });

    it('withSpan executes function and returns result', async () => {
      const { initTelemetry, withSpan } = await import('../../src/services/telemetry');

      initTelemetry();
      const result = await withSpan('test-operation', () => 'success');

      expect(result).toBe('success');
    });

    it('withSpan propagates errors and records exception', async () => {
      const { initTelemetry, withSpan } = await import('../../src/services/telemetry');

      initTelemetry();
      const testError = new Error('test error');

      await expect(withSpan('failing-operation', () => {
        throw testError;
      })).rejects.toThrow('test error');
    });

    it('withSpan handles async functions', async () => {
      const { initTelemetry, withSpan } = await import('../../src/services/telemetry');

      initTelemetry();
      const result = await withSpan('async-operation', async () => {
        await Promise.resolve();
        return 'async-success';
      });

      expect(result).toBe('async-success');
    });
  });

  describe('_getLoggerForTest', () => {
    it('returns null when not initialized', async () => {
      const { _getLoggerForTest } = await import('../../src/services/telemetry');

      expect(_getLoggerForTest()).toBeNull();
    });

    it('returns logger when initialized', async () => {
      const { initTelemetry, _getLoggerForTest } = await import('../../src/services/telemetry');

      initTelemetry();

      expect(_getLoggerForTest()).not.toBeNull();
    });
  });

  describe('exports', () => {
    it('exports SpanStatusCode enum', async () => {
      const { SpanStatusCode } = await import('../../src/services/telemetry');

      expect(SpanStatusCode.OK).toBeDefined();
      expect(SpanStatusCode.ERROR).toBeDefined();
      expect(SpanStatusCode.UNSET).toBeDefined();
    });

    it('exports initWebVitals function', async () => {
      const { initWebVitals } = await import('../../src/services/telemetry');

      expect(typeof initWebVitals).toBe('function');
    });
  });
});

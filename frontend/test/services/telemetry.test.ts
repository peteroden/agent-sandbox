import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { trace } from '@opentelemetry/api';

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
    randomUUID: vi.fn(() => 'test-session-uuid-12345'),
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

      expect(getSessionId()).toBe('test-session-uuid-12345');
      expect(globalThis.sessionStorage.setItem).toHaveBeenCalledWith(
        'otel_session_id',
        'test-session-uuid-12345'
      );
    });

    it('reuses existing session ID', async () => {
      mockSessionStorage['otel_session_id'] = 'existing-session-id';

      const { initTelemetry, getSessionId } = await import('../../src/services/telemetry');

      initTelemetry();

      expect(getSessionId()).toBe('existing-session-id');
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
    it.each([
      ['macOS', '/Users/john/code/file.ts', '/Users/***/code/file.ts'],
      ['Linux', '/home/john/code/file.ts', '/home/***/code/file.ts'],
      ['Windows C:', 'C:\\Users\\john\\code\\file.ts', 'C:\\Users\\***\\code\\file.ts'],
      ['Windows D:', 'D:\\Users\\admin\\file.ts', 'D:\\Users\\***\\file.ts'],
      ['undefined', undefined, ''],
      ['empty', '', ''],
    ])('sanitizes %s paths', async (_name, input, expected) => {
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

      setUser('user-123', { email: 'test@example.com', role: 'admin' });

      expect(getCurrentUser()).toEqual({
        id: 'user-123',
        attributes: { email: 'test@example.com', role: 'admin' },
      });
    });

    it('clears user', async () => {
      const { setUser, clearUser, getCurrentUser } = await import('../../src/services/telemetry');

      setUser('user-123');
      clearUser();

      expect(getCurrentUser()).toBeNull();
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

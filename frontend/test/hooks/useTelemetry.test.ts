import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, cleanup } from '@testing-library/preact'
import { TestDefaults } from '../test-constants'

// Local test constants for this file only
const SPAN_NAME = 'test-span'
const USER_ID = 'user-123'

// Logger test cases for parameterized tests
const LoggerTestCases: Array<{
  method: 'info' | 'warn' | 'error' | 'debug'
  message: string
  args: Record<string, string | number | boolean> | undefined
}> = [
  { method: 'info', message: 'Test info message', args: { key: 'value' } },
  { method: 'warn', message: 'Test warn message', args: undefined },
  { method: 'error', message: 'Test error message', args: { error: 'details' } },
  { method: 'debug', message: 'Test debug message', args: undefined },
]

// Mock sessionStorage
const mockSessionStorage: Record<string, string> = {}
Object.defineProperty(globalThis, 'sessionStorage', {
  value: {
    getItem: vi.fn((key: string) => mockSessionStorage[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      mockSessionStorage[key] = value
    }),
    removeItem: vi.fn((key: string) => {
      delete mockSessionStorage[key]
    }),
    clear: vi.fn(() => {
      Object.keys(mockSessionStorage).forEach((k) => delete mockSessionStorage[k])
    }),
  },
  writable: true,
})

// Mock crypto.randomUUID
Object.defineProperty(globalThis, 'crypto', {
  value: {
    randomUUID: vi.fn(() => TestDefaults.SESSION_ID),
  },
  writable: true,
})

// Hoist mock functions
const { mockSpanEnd, mockSetStatus, mockRecordException, mockSetAttribute, mockGetTracer, mockLogger } = vi.hoisted(() => ({
  mockSpanEnd: vi.fn(),
  mockSetStatus: vi.fn(),
  mockRecordException: vi.fn(),
  mockSetAttribute: vi.fn(),
  mockGetTracer: vi.fn(() => ({
    startSpan: vi.fn(() => ({
      end: mockSpanEnd,
      setStatus: mockSetStatus,
      recordException: mockRecordException,
      setAttribute: mockSetAttribute,
      addEvent: vi.fn(),
    })),
  })),
  mockLogger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}))

// Mock telemetry module
vi.mock('../../src/services/telemetry', () => ({
  getTracer: mockGetTracer,
  getSessionId: () => 'test-session-uuid-12345',
  logger: mockLogger,
  startSpan: vi.fn(() => ({
    end: mockSpanEnd,
    setStatus: mockSetStatus,
    recordException: mockRecordException,
    setAttribute: mockSetAttribute,
    addEvent: vi.fn(),
  })),
}))

describe('useTelemetry', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.keys(mockSessionStorage).forEach((k) => delete mockSessionStorage[k])
  })

  afterEach(() => cleanup())

  describe('hook returns', () => {
    it('returns createSpan function', async () => {
      const { useTelemetry } = await import('../../src/hooks/useTelemetry')
      const { result } = renderHook(() => useTelemetry())

      expect(typeof result.current.createSpan).toBe('function')
    })

    it('returns logger object', async () => {
      const { useTelemetry } = await import('../../src/hooks/useTelemetry')
      const { result } = renderHook(() => useTelemetry())

      expect(result.current.logger).toBeDefined()
      expect(typeof result.current.logger.info).toBe('function')
      expect(typeof result.current.logger.warn).toBe('function')
      expect(typeof result.current.logger.error).toBe('function')
      expect(typeof result.current.logger.debug).toBe('function')
    })

    it('returns sessionId', async () => {
      const { useTelemetry } = await import('../../src/hooks/useTelemetry')
      const { result } = renderHook(() => useTelemetry())

      expect(result.current.sessionId).toBe(TestDefaults.SESSION_ID)
    })
  })

  describe('createSpan', () => {
    it('creates a span with the given name', async () => {
      const { useTelemetry } = await import('../../src/hooks/useTelemetry')
      const { result } = renderHook(() => useTelemetry())

      const span = result.current.createSpan(SPAN_NAME)

      expect(span).toBeDefined()
      expect(typeof span.end).toBe('function')
    })

    it('creates a span with optional attributes', async () => {
      const { useTelemetry } = await import('../../src/hooks/useTelemetry')
      const { result } = renderHook(() => useTelemetry())

      const span = result.current.createSpan(SPAN_NAME, { 'user.id': USER_ID })

      expect(span).toBeDefined()
    })
  })

  describe('logger methods', () => {
    it.each(LoggerTestCases)(
      'logger.$method works correctly',
      async ({ method, message, args }) => {
        const { useTelemetry } = await import('../../src/hooks/useTelemetry')
        const { result } = renderHook(() => useTelemetry())

        if (args !== undefined) {
          result.current.logger[method](message, args)
          expect(mockLogger[method]).toHaveBeenCalledWith(message, args)
        } else {
          result.current.logger[method](message)
          expect(mockLogger[method]).toHaveBeenCalledWith(message)
        }
      }
    )
  })

  describe('hook stability', () => {
    it('returns stable references across re-renders', async () => {
      const { useTelemetry } = await import('../../src/hooks/useTelemetry')
      const { result, rerender } = renderHook(() => useTelemetry())

      const firstLogger = result.current.logger
      const firstCreateSpan = result.current.createSpan

      rerender()

      expect(result.current.logger).toBe(firstLogger)
      expect(result.current.createSpan).toBe(firstCreateSpan)
    })
  })
})

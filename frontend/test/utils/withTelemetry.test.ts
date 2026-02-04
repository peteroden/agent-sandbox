import { describe, it, expect, vi, beforeEach } from 'vitest'
import { SpanStatusCode } from '@opentelemetry/api'

// Local test constants for this file only
const OPERATION_NAME = 'test-operation'
const USER_ID = 'user-123'
const TEST_DATA = 'test-data'
const ERROR_TEST = 'Test error'
const ERROR_ORIGINAL = 'Original error'

// Hoist mock functions
const { mockSpanEnd, mockSetStatus, mockRecordException, mockAddEvent, mockStartSpan } = vi.hoisted(() => ({
  mockSpanEnd: vi.fn(),
  mockSetStatus: vi.fn(),
  mockRecordException: vi.fn(),
  mockAddEvent: vi.fn(),
  mockStartSpan: vi.fn(() => ({
    end: mockSpanEnd,
    setStatus: mockSetStatus,
    recordException: mockRecordException,
    addEvent: mockAddEvent,
    setAttribute: vi.fn(),
  })),
}))

// Mock telemetry module
vi.mock('../../src/services/telemetry', () => ({
  getTracer: () => ({
    startSpan: mockStartSpan,
  }),
  SpanStatusCode,
}))

describe('withTelemetry', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('span lifecycle', () => {
    it('creates a span with the given name', async () => {
      const { withTelemetry } = await import('../../src/utils/withTelemetry')

      await withTelemetry(OPERATION_NAME, async () => 'result')

      expect(mockStartSpan).toHaveBeenCalledWith(OPERATION_NAME, { attributes: undefined })
    })

    it('creates a span with optional attributes', async () => {
      const { withTelemetry } = await import('../../src/utils/withTelemetry')

      await withTelemetry(OPERATION_NAME, async () => 'result', { 'user.id': USER_ID })

      expect(mockStartSpan).toHaveBeenCalledWith(OPERATION_NAME, { 
        attributes: { 'user.id': USER_ID } 
      })
    })

    it('ends the span after the function completes', async () => {
      const { withTelemetry } = await import('../../src/utils/withTelemetry')

      await withTelemetry(OPERATION_NAME, async () => 'result')

      expect(mockSpanEnd).toHaveBeenCalledTimes(1)
    })

    it('sets span status to OK on success', async () => {
      const { withTelemetry } = await import('../../src/utils/withTelemetry')

      await withTelemetry(OPERATION_NAME, async () => 'result')

      expect(mockSetStatus).toHaveBeenCalledWith({ code: SpanStatusCode.OK })
    })

    it('returns the result of the wrapped function', async () => {
      const { withTelemetry } = await import('../../src/utils/withTelemetry')

      const result = await withTelemetry(OPERATION_NAME, async () => {
        return { data: TEST_DATA }
      })

      expect(result).toEqual({ data: TEST_DATA })
    })
  })

  describe('error handling', () => {
    it('sets span status to ERROR on failure', async () => {
      const { withTelemetry } = await import('../../src/utils/withTelemetry')

      await expect(
        withTelemetry(OPERATION_NAME, async () => {
          throw new Error(ERROR_TEST)
        })
      ).rejects.toThrow(ERROR_TEST)

      expect(mockSetStatus).toHaveBeenCalledWith({
        code: SpanStatusCode.ERROR,
        message: ERROR_TEST,
      })
    })

    it('records exception on failure', async () => {
      const { withTelemetry } = await import('../../src/utils/withTelemetry')
      const testError = new Error(ERROR_TEST)

      await expect(
        withTelemetry(OPERATION_NAME, async () => {
          throw testError
        })
      ).rejects.toThrow(ERROR_TEST)

      expect(mockRecordException).toHaveBeenCalledWith(testError)
    })

    it('ends the span even on failure', async () => {
      const { withTelemetry } = await import('../../src/utils/withTelemetry')

      await expect(
        withTelemetry(OPERATION_NAME, async () => {
          throw new Error(ERROR_TEST)
        })
      ).rejects.toThrow()

      expect(mockSpanEnd).toHaveBeenCalledTimes(1)
    })

    it('re-throws the original error', async () => {
      const { withTelemetry } = await import('../../src/utils/withTelemetry')
      const originalError = new Error(ERROR_ORIGINAL)

      await expect(
        withTelemetry(OPERATION_NAME, async () => {
          throw originalError
        })
      ).rejects.toBe(originalError)
    })
  })

  describe('async function handling', () => {
    it('waits for async functions to complete', async () => {
      const { withTelemetry } = await import('../../src/utils/withTelemetry')
      let completed = false

      await withTelemetry(OPERATION_NAME, async () => {
        await new Promise(resolve => setTimeout(resolve, 10))
        completed = true
        return 'done'
      })

      expect(completed).toBe(true)
    })

    it('handles nested async operations', async () => {
      const { withTelemetry } = await import('../../src/utils/withTelemetry')
      const results: string[] = []

      await withTelemetry('outer', async () => {
        results.push('outer-start')
        await withTelemetry('inner', async () => {
          results.push('inner')
          return 'inner-result'
        })
        results.push('outer-end')
        return 'outer-result'
      })

      expect(results).toEqual(['outer-start', 'inner', 'outer-end'])
    })
  })
})

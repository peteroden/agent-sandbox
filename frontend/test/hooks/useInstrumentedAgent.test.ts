import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, cleanup } from '@testing-library/preact'
import { TestDefaults } from '../test-constants'

// Hoist mock class
const { MockHttpAgent } = vi.hoisted(() => ({
  MockHttpAgent: vi.fn(function(this: { url: string }, config: { url: string }) {
    this.url = config.url
  }),
}))

// Mock @ag-ui/client
vi.mock('@ag-ui/client', () => ({
  HttpAgent: MockHttpAgent,
}))

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

// Mock telemetry
vi.mock('../../src/services/telemetry', () => ({
  getTracer: () => ({
    startSpan: vi.fn(() => ({
      end: vi.fn(),
      setStatus: vi.fn(),
      recordException: vi.fn(),
      setAttribute: vi.fn(),
      addEvent: vi.fn(),
    })),
  }),
  getSessionId: () => TestDefaults.SESSION_ID,
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}))

describe('useInstrumentedAgent', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.keys(mockSessionStorage).forEach((k) => delete mockSessionStorage[k])
    MockHttpAgent.mockClear()
  })

  afterEach(() => cleanup())

  describe('hook returns', () => {
    it('returns an agent instance', async () => {
      const { useInstrumentedAgent } = await import('../../src/hooks/useInstrumentedAgent')
      const { result } = renderHook(() => useInstrumentedAgent({ url: TestDefaults.API_URL }))

      expect(result.current.agent).toBeDefined()
    })

    it('creates HttpAgent with the given URL', async () => {
      const { useInstrumentedAgent } = await import('../../src/hooks/useInstrumentedAgent')
      renderHook(() => useInstrumentedAgent({ url: TestDefaults.API_URL_CUSTOM }))

      expect(MockHttpAgent).toHaveBeenCalledWith({ url: TestDefaults.API_URL_CUSTOM })
    })

    it('returns sessionId from telemetry', async () => {
      const { useInstrumentedAgent } = await import('../../src/hooks/useInstrumentedAgent')
      const { result } = renderHook(() => useInstrumentedAgent({ url: TestDefaults.API_URL }))

      expect(result.current.sessionId).toBe(TestDefaults.SESSION_ID)
    })
  })

  describe('agent memoization', () => {
    it('returns the same agent instance on re-render with same URL', async () => {
      const { useInstrumentedAgent } = await import('../../src/hooks/useInstrumentedAgent')
      const { result, rerender } = renderHook(() => useInstrumentedAgent({ url: TestDefaults.API_URL }))

      const firstAgent = result.current.agent

      rerender()

      expect(result.current.agent).toBe(firstAgent)
      expect(MockHttpAgent).toHaveBeenCalledTimes(1)
    })

    it('creates a new agent when URL changes', async () => {
      const { useInstrumentedAgent } = await import('../../src/hooks/useInstrumentedAgent')
      
      let url: string = TestDefaults.API_URL
      const { result, rerender } = renderHook(() => useInstrumentedAgent({ url }))

      const firstAgent = result.current.agent

      url = TestDefaults.API_URL_V2
      rerender()

      expect(result.current.agent).not.toBe(firstAgent)
      expect(MockHttpAgent).toHaveBeenCalledTimes(2)
    })
  })

  describe('telemetry context', () => {
    it('agent has access to telemetry context via sessionId', async () => {
      const { useInstrumentedAgent } = await import('../../src/hooks/useInstrumentedAgent')
      const { result } = renderHook(() => useInstrumentedAgent({ url: TestDefaults.API_URL }))

      // The hook provides sessionId that can be used for trace correlation
      expect(result.current.sessionId).toBe(TestDefaults.SESSION_ID)
      expect(result.current.agent).toBeDefined()
    })
  })

  describe('return type', () => {
    it('returns UseInstrumentedAgentReturn interface', async () => {
      const { useInstrumentedAgent } = await import('../../src/hooks/useInstrumentedAgent')
      const { result } = renderHook(() => useInstrumentedAgent({ url: TestDefaults.API_URL }))

      expect(result.current).toHaveProperty('agent')
      expect(result.current).toHaveProperty('sessionId')
    })
  })
})

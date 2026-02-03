import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, cleanup } from '@testing-library/preact'
import { useChat, type ToolHandler } from '../../src/hooks/useChat'
import type { AgentSubscriber, Tool } from '@ag-ui/client'

// Hoist mock functions so they can be referenced in vi.mock
const { mockSpanEnd, mockSpanAddEvent, mockStartSpan, mockLogger } = vi.hoisted(() => ({
  mockSpanEnd: vi.fn(),
  mockSpanAddEvent: vi.fn(),
  mockStartSpan: vi.fn((_name?: string, _options?: Record<string, unknown>) => ({
    end: vi.fn(),
    addEvent: vi.fn(),
  })),
  mockLogger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('../../src/services/telemetry', () => ({
  getTracer: () => ({
    startSpan: vi.fn(() => ({
      setAttribute: vi.fn(),
      setStatus: vi.fn(),
      recordException: vi.fn(),
      end: vi.fn(),
    })),
  }),
  startSpan: (_name?: string, _options?: Record<string, unknown>) => {
    mockStartSpan(_name, _options)
    return {
      end: mockSpanEnd,
      addEvent: mockSpanAddEvent,
    }
  },
  logger: mockLogger,
}))

// Mock HttpAgent
const mockAddMessage = vi.fn()
const mockSetMessages = vi.fn()
const mockRunAgent = vi.fn().mockResolvedValue({})
const mockSubscribe = vi.fn()
let subscriber: AgentSubscriber | null = null

vi.mock('@ag-ui/client', async (importOriginal) => {
  const original = await importOriginal() as Record<string, unknown>
  return {
    ...original,
    HttpAgent: class MockHttpAgent {
      url: string
      constructor(config: { url: string }) {
        this.url = config.url
      }
      addMessage = mockAddMessage
      setMessages = mockSetMessages
      runAgent = mockRunAgent
      subscribe = (sub: AgentSubscriber) => {
        subscriber = sub
        mockSubscribe(sub)
        return { unsubscribe: vi.fn() }
      }
    },
  }
})

vi.stubGlobal('crypto', { randomUUID: () => 'test-uuid' })

// Helper to trigger subscriber events - functions return void for act() compatibility
const trigger = {
  messages: (messages: Array<{ id: string; role: string; content: string }>): void => {
    subscriber?.onMessagesChanged?.({ messages, state: {}, agent: {} } as never)
  },
  event: (event: { type: string }): void => {
    subscriber?.onEvent?.({ event, messages: [], state: {}, agent: {}, input: {} } as never)
  },
  toolCallStart: (toolCallId: string, toolCallName: string): void => {
    subscriber?.onToolCallStartEvent?.({ event: { type: 'TOOL_CALL_START', toolCallId, toolCallName }, messages: [], state: {}, agent: {}, input: {} } as never)
  },
  toolCallArgs: (toolCallId: string, delta: string): void => {
    subscriber?.onToolCallArgsEvent?.({ event: { type: 'TOOL_CALL_ARGS', toolCallId, delta }, toolCallBuffer: delta, toolCallName: '', partialToolCallArgs: {}, messages: [], state: {}, agent: {}, input: {} } as never)
  },
  toolCallEnd: (toolCallId: string): void => {
    subscriber?.onToolCallEndEvent?.({ event: { type: 'TOOL_CALL_END', toolCallId }, toolCallName: '', toolCallArgs: {}, messages: [], state: {}, agent: {}, input: {} } as never)
  },
  runStart: (): void => {
    subscriber?.onRunStartedEvent?.({ event: { type: 'RUN_STARTED', threadId: 't', runId: 'r' }, messages: [], state: {}, agent: {}, input: {} } as never)
  },
  runEnd: (): void => {
    subscriber?.onRunFinishedEvent?.({ event: { type: 'RUN_FINISHED', threadId: 't', runId: 'r' }, messages: [], state: {}, agent: {}, input: {} } as never)
  },
  runError: (message: string): void => {
    subscriber?.onRunErrorEvent?.({ event: { type: 'RUN_ERROR', message }, messages: [], state: {}, agent: {}, input: {} } as never)
  },
}

describe('useChat', () => {
  const url = '/api'

  beforeEach(() => {
    vi.clearAllMocks()
    subscriber = null
  })

  afterEach(() => cleanup())

  describe('initialization', () => {
    it('returns initial state and functions', () => {
      const { result } = renderHook(() => useChat({ url }))

      expect(result.current.messages).toEqual([])
      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).toBeNull()
      expect(typeof result.current.sendMessage).toBe('function')
      expect(typeof result.current.clearMessages).toBe('function')
      expect(typeof result.current.addToolResult).toBe('function')
    })
  })

  describe('sendMessage', () => {
    it('adds user message and calls runAgent with tools', async () => {
      const tools: Tool[] = [{ name: 'test', description: 'test', parameters: {} }]
      const { result } = renderHook(() => useChat({ url, tools }))

      await act(() => result.current.sendMessage('Hello'))

      expect(mockAddMessage).toHaveBeenCalledWith({ id: 'test-uuid', role: 'user', content: 'Hello' })
      expect(mockRunAgent).toHaveBeenCalledWith({ tools })
    })

    it('manages loading state', async () => {
      let resolve: (value?: unknown) => void
      mockRunAgent.mockImplementationOnce(() => new Promise(r => { resolve = r }))
      const { result } = renderHook(() => useChat({ url }))

      act(() => { result.current.sendMessage('Hello') })
      expect(result.current.isLoading).toBe(true)

      await act(async () => { 
        resolve!()
        // Extra tick for context.with wrapper to complete
        await Promise.resolve()
      })
      expect(result.current.isLoading).toBe(false)
    })

    it('sets error on failure and calls onError', async () => {
      const onError = vi.fn()
      mockRunAgent.mockRejectedValueOnce(new Error('Failed'))
      const { result } = renderHook(() => useChat({ url, onError }))

      await act(() => result.current.sendMessage('Hello'))

      expect(result.current.error?.message).toBe('Failed')
      expect(onError).toHaveBeenCalled()
    })

    it('prevents concurrent sends', async () => {
      let resolve: (value?: unknown) => void
      mockRunAgent.mockImplementation(() => new Promise(r => { resolve = r }))
      const { result } = renderHook(() => useChat({ url }))

      act(() => { result.current.sendMessage('First') })
      await act(() => result.current.sendMessage('Second'))

      expect(mockAddMessage).toHaveBeenCalledTimes(1)
      await act(async () => { resolve!() })
    })

    it('should not recreate sendMessage callback when isLoading changes', async () => {
      let resolve: (value?: unknown) => void
      mockRunAgent.mockImplementation(() => new Promise(r => { resolve = r }))
      const { result } = renderHook(() => useChat({ url }))

      const sendMessage1 = result.current.sendMessage

      // Trigger loading state change
      act(() => { result.current.sendMessage('test') })

      const sendMessage2 = result.current.sendMessage

      // Callback reference should be stable
      expect(sendMessage1).toBe(sendMessage2)

      await act(async () => { resolve!() })

      const sendMessage3 = result.current.sendMessage
      expect(sendMessage1).toBe(sendMessage3)
    })
  })

  describe('clearMessages', () => {
    it('clears messages and error state', async () => {
      mockRunAgent.mockRejectedValueOnce(new Error('Error'))
      const { result } = renderHook(() => useChat({ url }))

      await act(() => result.current.sendMessage('Hello'))
      expect(result.current.error).not.toBeNull()

      act(() => result.current.clearMessages())

      expect(mockSetMessages).toHaveBeenCalledWith([])
      expect(result.current.messages).toEqual([])
      expect(result.current.error).toBeNull()
    })
  })

  describe('addToolResult', () => {
    it('adds tool message to agent', () => {
      const { result } = renderHook(() => useChat({ url }))

      act(() => result.current.addToolResult('tc-123', 'Tool output'))

      expect(mockAddMessage).toHaveBeenCalledWith({
        id: 'test-uuid',
        role: 'tool',
        toolCallId: 'tc-123',
        content: 'Tool output',
      })
    })
  })

  describe('event callbacks', () => {
    it('updates messages from subscriber', async () => {
      const { result } = renderHook(() => useChat({ url }))

      await act(() => trigger.messages([{ id: '1', role: 'user', content: 'Hi' }]))

      expect(result.current.messages).toEqual([{ id: '1', role: 'user', content: 'Hi' }])
    })

    it('calls onEvent callback', async () => {
      const onEvent = vi.fn()
      renderHook(() => useChat({ url, onEvent }))

      await act(() => trigger.event({ type: 'TEXT_MESSAGE_CONTENT' }))

      expect(onEvent).toHaveBeenCalledWith({ type: 'TEXT_MESSAGE_CONTENT' })
    })

    it('calls onRunStart and onRunEnd callbacks', async () => {
      const onRunStart = vi.fn()
      const onRunEnd = vi.fn()
      renderHook(() => useChat({ url, onRunStart, onRunEnd }))

      await act(() => trigger.runStart())
      expect(onRunStart).toHaveBeenCalled()

      await act(() => trigger.runEnd())
      expect(onRunEnd).toHaveBeenCalled()
    })

    it('sets error from run error event', async () => {
      const onError = vi.fn()
      const { result } = renderHook(() => useChat({ url, onError }))

      await act(() => trigger.runError('Something failed'))

      expect(result.current.error?.message).toBe('Something failed')
      expect(onError).toHaveBeenCalled()
    })
  })

  describe('tool call handling', () => {
    it('calls onToolCallStart and onToolCallEnd with accumulated args', async () => {
      const onToolCallStart = vi.fn()
      const onToolCallEnd = vi.fn()
      renderHook(() => useChat({ url, onToolCallStart, onToolCallEnd }))

      await act(() => trigger.toolCallStart('tc-1', 'myTool'))
      expect(onToolCallStart).toHaveBeenCalledWith('myTool', 'tc-1')

      await act(() => trigger.toolCallArgs('tc-1', '{"key":'))
      await act(() => trigger.toolCallArgs('tc-1', '"value"}'))
      await act(() => trigger.toolCallEnd('tc-1'))

      expect(onToolCallEnd).toHaveBeenCalledWith('tc-1', 'myTool', '{"key":"value"}')
    })

    it('auto-executes tool handler and continues conversation', async () => {
      const handler: ToolHandler = vi.fn().mockResolvedValue('result')
      const tools: Tool[] = [{ name: 'myTool', description: 'test', parameters: {} }]
      renderHook(() => useChat({ url, tools, toolHandlers: { myTool: handler } }))

      await act(() => trigger.toolCallStart('tc-1', 'myTool'))
      await act(() => trigger.toolCallArgs('tc-1', '{"x":1}'))
      await act(() => trigger.toolCallEnd('tc-1'))

      expect(handler).toHaveBeenCalledWith({ x: 1 })
      expect(mockAddMessage).toHaveBeenCalledWith(expect.objectContaining({
        role: 'tool',
        toolCallId: 'tc-1',
        content: 'result',
      }))
      expect(mockRunAgent).toHaveBeenCalledWith({ tools })
    })

    it('handles tool handler errors', async () => {
      const onError = vi.fn()
      const handler: ToolHandler = vi.fn().mockRejectedValue(new Error('Handler failed'))
      const { result } = renderHook(() => useChat({ url, onError, toolHandlers: { myTool: handler } }))

      await act(() => trigger.toolCallStart('tc-1', 'myTool'))
      await act(() => trigger.toolCallArgs('tc-1', '{}'))
      await act(() => trigger.toolCallEnd('tc-1'))
      
      // Wait for async handler to complete
      await act(() => new Promise(resolve => setTimeout(resolve, 10)))

      expect(result.current.error?.message).toBe('Handler failed')
      expect(onError).toHaveBeenCalled()
    })
  })

  describe('agent export', () => {
    it('exposes agent instance', () => {
      const { result } = renderHook(() => useChat({ url }))

      expect(result.current.agent).toBeDefined()
      expect(result.current.agent.url).toBe(url)
    })
  })

  describe('telemetry', () => {
    beforeEach(() => {
      mockStartSpan.mockClear()
      mockSpanEnd.mockClear()
      mockSpanAddEvent.mockClear()
    })

    it('does not track spans when enableTelemetry is false', async () => {
      renderHook(() => useChat({ url, enableTelemetry: false }))

      await act(() => trigger.toolCallStart('tc-1', 'myTool'))
      await act(() => trigger.toolCallEnd('tc-1'))

      expect(mockStartSpan).not.toHaveBeenCalled()
    })

    it('starts span on tool call start when telemetry enabled', async () => {
      renderHook(() => useChat({ url, enableTelemetry: true }))

      await act(() => trigger.toolCallStart('tc-1', 'myTool'))

      expect(mockStartSpan).toHaveBeenCalledWith('agui.tool_call', {
        attributes: {
          'tool.call_id': 'tc-1',
          'tool.name': 'myTool',
        },
      })
    })

    it('ends span on tool call end when telemetry enabled', async () => {
      renderHook(() => useChat({ url, enableTelemetry: true }))

      await act(() => trigger.toolCallStart('tc-1', 'myTool'))
      await act(() => trigger.toolCallEnd('tc-1'))

      expect(mockSpanEnd).toHaveBeenCalled()
    })

    it('adds events to active tool spans', async () => {
      renderHook(() => useChat({ url, enableTelemetry: true }))

      await act(() => trigger.toolCallStart('tc-1', 'myTool'))
      await act(() => trigger.event({ type: 'SOME_EVENT' }))

      expect(mockSpanAddEvent).toHaveBeenCalledWith('SOME_EVENT')
    })

    it('ends orphaned spans on cleanup', async () => {
      const { unmount } = renderHook(() => useChat({ url, enableTelemetry: true }))

      await act(() => trigger.toolCallStart('tc-1', 'myTool'))
      
      unmount()

      expect(mockSpanEnd).toHaveBeenCalled()
    })
  })
})

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, cleanup } from '@testing-library/preact'
import { useMcpChat } from '../../src/hooks/useMcpChat'

// Test constants
const TOOL_NAME = 'test-tool'
const USER_MESSAGE = 'Hello, agent!'
const ASSISTANT_MESSAGE = 'Hello! How can I help you?'
const TOOL_CALL_ERROR = 'Tool call failed'

// Hoist mock functions
const { mockCallTool } = vi.hoisted(() => ({
  mockCallTool: vi.fn().mockResolvedValue([{ type: 'text', text: 'Tool result' }]),
}))

vi.mock('../../src/services/mcpClient', () => ({
  mcpClient: {
    callTool: mockCallTool,
    get isConnected() {
      return true
    },
  },
}))

vi.stubGlobal('crypto', { randomUUID: () => 'test-uuid' })

describe('useMcpChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  describe('initialization', () => {
    it('returns empty messages initially', () => {
      const { result } = renderHook(() => useMcpChat())

      expect(result.current.messages).toEqual([])
      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).toBeNull()
      expect(typeof result.current.addMessage).toBe('function')
      expect(typeof result.current.callTool).toBe('function')
      expect(typeof result.current.clearMessages).toBe('function')
    })
  })

  describe('addMessage', () => {
    it('adds user message to history', () => {
      const { result } = renderHook(() => useMcpChat())

      act(() => {
        result.current.addMessage('user', USER_MESSAGE)
      })

      expect(result.current.messages).toEqual([
        { id: 'test-uuid', role: 'user', content: USER_MESSAGE },
      ])
    })

    it('adds assistant message to history', () => {
      const { result } = renderHook(() => useMcpChat())

      act(() => {
        result.current.addMessage('assistant', ASSISTANT_MESSAGE)
      })

      expect(result.current.messages).toEqual([
        { id: 'test-uuid', role: 'assistant', content: ASSISTANT_MESSAGE },
      ])
    })

    it('adds tool message with result', () => {
      const { result } = renderHook(() => useMcpChat())
      const toolResult = [{ type: 'text', text: 'Result' }]

      act(() => {
        result.current.addMessage('tool', 'Tool executed', toolResult)
      })

      expect(result.current.messages).toEqual([
        { id: 'test-uuid', role: 'tool', content: 'Tool executed', toolResult },
      ])
    })
  })

  describe('callTool', () => {
    it('invokes tool and adds result as assistant message', async () => {
      const toolResult = [{ type: 'text', text: 'Tool output' }]
      mockCallTool.mockResolvedValueOnce(toolResult)

      const { result } = renderHook(() => useMcpChat())

      await act(() => result.current.callTool(TOOL_NAME, { arg: 'value' }))

      expect(mockCallTool).toHaveBeenCalledWith(TOOL_NAME, { arg: 'value' })
      expect(result.current.messages).toContainEqual(
        expect.objectContaining({
          role: 'assistant',
          content: 'Tool output',
          toolResult,
        })
      )
    })

    it('handles loading state during tool call', async () => {
      let resolveCall: (value: unknown) => void
      mockCallTool.mockImplementationOnce(() => new Promise(r => { resolveCall = r }))

      const { result } = renderHook(() => useMcpChat())

      act(() => { result.current.callTool(TOOL_NAME, {}) })
      expect(result.current.isLoading).toBe(true)

      await act(async () => {
        resolveCall!([{ type: 'text', text: 'Done' }])
        await new Promise(resolve => setTimeout(resolve, 10))
      })
      expect(result.current.isLoading).toBe(false)
    })

    it('adds error message on tool call failure', async () => {
      mockCallTool.mockRejectedValueOnce(new Error(TOOL_CALL_ERROR))

      const { result } = renderHook(() => useMcpChat())

      await act(() => result.current.callTool(TOOL_NAME, {}))

      // Error is added as an assistant message
      expect(result.current.messages).toContainEqual(
        expect.objectContaining({
          role: 'assistant',
          content: `Error: ${TOOL_CALL_ERROR}`,
        })
      )
    })
  })

  describe('clearMessages', () => {
    it('clears all messages', async () => {
      const { result } = renderHook(() => useMcpChat())

      act(() => { result.current.addMessage('user', USER_MESSAGE) })
      act(() => { result.current.addMessage('assistant', ASSISTANT_MESSAGE) })

      expect(result.current.messages.length).toBeGreaterThan(0)

      act(() => { result.current.clearMessages() })

      expect(result.current.messages).toEqual([])
      expect(result.current.error).toBeNull()
    })
  })

  describe('message order', () => {
    it('maintains message order', () => {
      const { result } = renderHook(() => useMcpChat())

      act(() => {
        result.current.addMessage('user', 'First')
        result.current.addMessage('assistant', 'Second')
        result.current.addMessage('user', 'Third')
      })

      expect(result.current.messages.map(m => m.content)).toEqual([
        'First', 'Second', 'Third',
      ])
    })
  })
})

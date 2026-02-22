import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, cleanup } from '@testing-library/preact'
import { useMcpConnection } from '../../src/hooks/useMcpConnection'
import { TestDefaults } from '../test-constants'

// Test constants
const TOOL_ONE = 'tool-one'
const TOOL_TWO = 'tool-two'
const CONNECTION_ERROR = 'Connection failed'
const LIST_ERROR = 'Failed to list tools'

// Hoist mock functions
const { mockConnect, mockDisconnect, mockListTools } = vi.hoisted(() => ({
  mockConnect: vi.fn().mockResolvedValue(undefined),
  mockDisconnect: vi.fn().mockResolvedValue(undefined),
  mockListTools: vi.fn().mockResolvedValue([]),
}))

// Track connection state
let connected = false

vi.mock('../../src/services/mcpClient', () => ({
  mcpClient: {
    connect: async (url: string) => {
      await mockConnect(url)
      connected = true
    },
    disconnect: async () => {
      await mockDisconnect()
      connected = false
    },
    listTools: mockListTools,
    get isConnected() {
      return connected
    },
  },
}))

describe('useMcpConnection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    connected = false
  })

  afterEach(() => {
    cleanup()
  })

  describe('initialization', () => {
    it('returns initial state with no connection', () => {
      const { result } = renderHook(() =>
        useMcpConnection({ url: TestDefaults.MCP_URL })
      )

      expect(result.current.isConnected).toBe(false)
      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).toBeNull()
      expect(result.current.tools).toEqual([])
      expect(typeof result.current.connect).toBe('function')
      expect(typeof result.current.disconnect).toBe('function')
    })

    it('auto-connects when autoConnect is true', async () => {
      const { result } = renderHook(() =>
        useMcpConnection({ url: TestDefaults.MCP_URL, autoConnect: true })
      )

      // Wait for auto-connect
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 10))
      })

      expect(mockConnect).toHaveBeenCalledWith(TestDefaults.MCP_URL)
      expect(result.current.isConnected).toBe(true)
    })

    it('does not auto-connect when autoConnect is false', () => {
      renderHook(() =>
        useMcpConnection({ url: TestDefaults.MCP_URL, autoConnect: false })
      )

      expect(mockConnect).not.toHaveBeenCalled()
    })
  })

  describe('connect', () => {
    it('establishes connection and fetches tools', async () => {
      const mockTools = [
        { name: TOOL_ONE, description: 'Tool one' },
        { name: TOOL_TWO },
      ]
      mockListTools.mockResolvedValueOnce(mockTools)

      const { result } = renderHook(() =>
        useMcpConnection({ url: TestDefaults.MCP_URL })
      )

      await act(() => result.current.connect())

      expect(mockConnect).toHaveBeenCalledWith(TestDefaults.MCP_URL)
      expect(mockListTools).toHaveBeenCalled()
      expect(result.current.isConnected).toBe(true)
      expect(result.current.tools).toEqual(mockTools)
    })

    it('handles loading state during connection', async () => {
      let resolveConnect: () => void
      mockConnect.mockImplementationOnce(() => new Promise<void>(r => { resolveConnect = r }))

      const { result } = renderHook(() =>
        useMcpConnection({ url: TestDefaults.MCP_URL })
      )

      act(() => { result.current.connect() })
      expect(result.current.isLoading).toBe(true)

      await act(async () => {
        resolveConnect!()
        // Wait for listTools to complete too
        await new Promise(resolve => setTimeout(resolve, 10))
      })
      expect(result.current.isLoading).toBe(false)
    })

    it('sets error on connection failure', async () => {
      mockConnect.mockRejectedValueOnce(new Error(CONNECTION_ERROR))

      const { result } = renderHook(() =>
        useMcpConnection({ url: TestDefaults.MCP_URL })
      )

      await act(() => result.current.connect())

      expect(result.current.error?.message).toBe(CONNECTION_ERROR)
      expect(result.current.isConnected).toBe(false)
    })

    it('sets error on list tools failure', async () => {
      mockListTools.mockRejectedValueOnce(new Error(LIST_ERROR))

      const { result } = renderHook(() =>
        useMcpConnection({ url: TestDefaults.MCP_URL })
      )

      await act(() => result.current.connect())

      expect(result.current.error?.message).toBe(LIST_ERROR)
    })
  })

  describe('disconnect', () => {
    it('closes connection and clears tools', async () => {
      mockListTools.mockResolvedValueOnce([{ name: TOOL_ONE }])

      const { result } = renderHook(() =>
        useMcpConnection({ url: TestDefaults.MCP_URL })
      )

      await act(() => result.current.connect())
      expect(result.current.tools.length).toBe(1)

      await act(() => result.current.disconnect())

      expect(mockDisconnect).toHaveBeenCalled()
      expect(result.current.isConnected).toBe(false)
      expect(result.current.tools).toEqual([])
    })
  })

  describe('cleanup', () => {
    it('disconnects on unmount when connected', async () => {
      const { result, unmount } = renderHook(() =>
        useMcpConnection({ url: TestDefaults.MCP_URL })
      )

      await act(() => result.current.connect())

      unmount()

      expect(mockDisconnect).toHaveBeenCalled()
    })

    it('does not disconnect on unmount when not connected', () => {
      const { unmount } = renderHook(() =>
        useMcpConnection({ url: TestDefaults.MCP_URL })
      )

      unmount()

      expect(mockDisconnect).not.toHaveBeenCalled()
    })
  })

  describe('url changes', () => {
    it('reconnects when url changes and connected', async () => {
      const { result, rerender } = renderHook(
        ({ url }: { url: string }) => useMcpConnection({ url }),
        { initialProps: { url: TestDefaults.MCP_URL as string } }
      )

      await act(() => result.current.connect())
      vi.clearAllMocks()

      rerender({ url: TestDefaults.MCP_URL_CUSTOM as string })

      // Should disconnect first, then reconnect
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 10))
      })
      
      expect(mockDisconnect).toHaveBeenCalled()
      expect(mockConnect).toHaveBeenCalledWith(TestDefaults.MCP_URL_CUSTOM)
    })
  })
})

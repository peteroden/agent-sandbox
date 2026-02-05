import { useState, useCallback, useEffect, useRef } from 'preact/hooks'
import { mcpClient, type Tool } from '../services/mcpClient'

export type { Tool }

export interface UseMcpConnectionOptions {
  /** URL of the MCP server endpoint */
  url: string
  /** Whether to connect automatically on mount */
  autoConnect?: boolean
}

export interface UseMcpConnectionReturn {
  /** Whether currently connected to the MCP server */
  isConnected: boolean
  /** Whether a connection operation is in progress */
  isLoading: boolean
  /** Any error that occurred during connection */
  error: Error | null
  /** List of available tools from the server */
  tools: Tool[]
  /** Connect to the MCP server */
  connect: () => Promise<void>
  /** Disconnect from the MCP server */
  disconnect: () => Promise<void>
}

/**
 * Hook for managing MCP server connection state.
 * Handles connecting, disconnecting, and fetching available tools.
 */
export function useMcpConnection(options: UseMcpConnectionOptions): UseMcpConnectionReturn {
  const { url, autoConnect = false } = options

  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [tools, setTools] = useState<Tool[]>([])
  
  const urlRef = useRef(url)
  const connectedRef = useRef(false)

  const connect = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      await mcpClient.connect(urlRef.current)
      connectedRef.current = true
      setIsConnected(true)
      
      // Fetch tools after connecting
      const availableTools = await mcpClient.listTools()
      setTools(availableTools)
    } catch (err) {
      const connectionError = err instanceof Error ? err : new Error(String(err))
      setError(connectionError)
      connectedRef.current = false
      setIsConnected(false)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const disconnect = useCallback(async () => {
    await mcpClient.disconnect()
    connectedRef.current = false
    setIsConnected(false)
    setTools([])
  }, [])

  // Handle URL changes - reconnect if connected
  useEffect(() => {
    const previousUrl = urlRef.current
    urlRef.current = url

    if (connectedRef.current && previousUrl !== url) {
      // Reconnect with new URL
      disconnect().then(() => connect())
    }
  }, [url, disconnect, connect])

  // Auto-connect on mount if requested
  useEffect(() => {
    if (autoConnect) {
      connect()
    }
  }, [autoConnect, connect])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (connectedRef.current) {
        mcpClient.disconnect()
      }
    }
  }, [])

  return {
    isConnected,
    isLoading,
    error,
    tools,
    connect,
    disconnect,
  }
}

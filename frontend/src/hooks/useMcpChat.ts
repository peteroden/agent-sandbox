import { useState, useCallback } from 'preact/hooks'
import { mcpClient, type ContentItem } from '../services/mcpClient'
import { logger, withSpan } from '@agent-sandbox/otel-web-sdk'

const UI_URI_PATTERN = /ui:\/\/[^\s"'}\]]+/g

/**
 * Extracts ui:// URIs from text content, used to detect MCP App views
 * referenced in tool responses.
 */
export function extractViewUris(text: string): string[] {
  return [...new Set(text.match(UI_URI_PATTERN) ?? [])]
}

/**
 * Fetches MCP App HTML from the backend resource proxy.
 */
async function fetchResourceHtml(uri: string): Promise<string> {
  const response = await fetch(
    `/api/mcp-resource?uri=${encodeURIComponent(uri)}`,
  )
  if (!response.ok) {
    throw new Error(`Failed to fetch resource: ${response.statusText}`)
  }
  return response.text()
}

/**
 * Message in the MCP chat conversation
 */
export interface McpMessage {
  id: string
  role: 'user' | 'assistant' | 'tool'
  content: string
  toolResult?: ContentItem[]
}

export interface UseMcpChatReturn {
  /** List of messages in the conversation */
  messages: McpMessage[]
  /** Whether a tool call is in progress */
  isLoading: boolean
  /** Any error that occurred */
  error: Error | null
  /** Add a message to the conversation */
  addMessage: (role: 'user' | 'assistant' | 'tool', content: string, toolResult?: ContentItem[]) => void
  /** Call a tool and add the result as a message */
  callTool: (name: string, args: Record<string, unknown>) => Promise<void>
  /** Clear all messages and errors */
  clearMessages: () => void
}

/**
 * Hook for managing MCP chat conversation state.
 * Provides message history and tool invocation capabilities.
 *
 * When a tool response contains ui:// URIs (MCP App views), the hook
 * automatically fetches the HTML from the backend resource proxy
 * and appends it as renderable content.
 */
export function useMcpChat(): UseMcpChatReturn {
  const [messages, setMessages] = useState<McpMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const addMessage = useCallback((
    role: 'user' | 'assistant' | 'tool',
    content: string,
    toolResult?: ContentItem[]
  ) => {
    const message: McpMessage = {
      id: crypto.randomUUID(),
      role,
      content,
      toolResult,
    }
    setMessages(prev => [...prev, message])
  }, [])

  const callTool = useCallback(async (name: string, args: Record<string, unknown>) => {
    setIsLoading(true)
    setError(null)

    try {
      const result = await withSpan('mcp.call_tool', async (span) => {
        span.setAttribute('tool.name', name)
        logger.info('Calling MCP tool', { 'tool.name': name })
        
        const toolResult = await mcpClient.callTool(name, args)
        
        logger.info('MCP tool completed', { 'tool.name': name })
        return toolResult
      })
      
      // Extract text content from result
      const textContent = result
        .filter(item => item.type === 'text' && item.text)
        .map(item => item.text)
        .join('\n')

      // Detect ui:// URIs in text and fetch HTML views
      const viewUris = extractViewUris(textContent)
      for (const uri of viewUris) {
        try {
          const html = await fetchResourceHtml(uri)
          result.push({ type: 'resource', uri, htmlContent: html })
        } catch (e) {
          logger.error('Failed to fetch MCP App view', { uri, error: String(e) })
        }
      }
      
      // Add assistant response as message
      addMessage('assistant', textContent || 'No response', result)
    } catch (err) {
      const toolError = err instanceof Error ? err : new Error(String(err))
      logger.error('MCP tool failed', { 'tool.name': name, 'error.message': toolError.message })
      setError(toolError)
      // Add error as assistant message
      addMessage('assistant', `Error: ${toolError.message}`)
    } finally {
      setIsLoading(false)
    }
  }, [addMessage])

  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
  }, [])

  return {
    messages,
    isLoading,
    error,
    addMessage,
    callTool,
    clearMessages,
  }
}

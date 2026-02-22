import { useState, useEffect } from 'preact/hooks'
import type { FunctionComponent } from 'preact'
import { useMcpConnection } from '../hooks/useMcpConnection'
import { useMcpChat, type McpMessage } from '../hooks/useMcpChat'
import { McpToolRenderer } from '../components/McpToolRenderer'

const MCP_SERVER_URL = '/mcp'
const AGENT_TOOL_NAME = 'AGUIAssistant'

/**
 * MCP Chat page - chat interface using AGUIAssistant via MCP protocol
 */
export const McpChat: FunctionComponent = () => {
  const [inputValue, setInputValue] = useState('')

  const {
    isConnected,
    isLoading: connectionLoading,
    error: connectionError,
    connect,
  } = useMcpConnection({ url: MCP_SERVER_URL })

  const {
    messages,
    isLoading: chatLoading,
    error: chatError,
    addMessage,
    callTool,
    clearMessages,
  } = useMcpChat()

  // Auto-connect on mount
  useEffect(() => {
    if (!isConnected && !connectionLoading) {
      connect()
    }
  }, [])

  const handleSubmit = async (e: Event) => {
    e.preventDefault()
    const userMessage = inputValue.trim()
    if (!userMessage || !isConnected) return

    // Add user message
    addMessage('user', userMessage)
    setInputValue('')

    // Call AGUIAssistant with the task
    await callTool(AGENT_TOOL_NAME, { task: userMessage })
  }

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto p-4">
      {/* Header */}
      <div className="mb-4 p-4 bg-white rounded-lg shadow">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-800">MCP Chat</h1>
            <p className="text-sm text-gray-500">
              Chat with {AGENT_TOOL_NAME} via MCP protocol
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`w-3 h-3 rounded-full ${
                isConnected ? 'bg-green-500' : connectionLoading ? 'bg-yellow-500' : 'bg-red-500'
              }`}
            />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : connectionLoading ? 'Connecting...' : 'Disconnected'}
            </span>
          </div>
        </div>

        {connectionError && (
          <div className="text-red-600 text-sm mt-2">
            Connection error: {connectionError.message}
          </div>
        )}
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col bg-white rounded-lg shadow min-h-0">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <p className="text-gray-500 text-center py-8">
              {isConnected 
                ? 'Send a message to start chatting'
                : 'Connecting to MCP server...'}
            </p>
          )}
          
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </div>

        {/* Input Area */}
        <div className="border-t p-4">
          {chatError && (
            <div className="text-red-600 text-sm mb-2">
              Error: {chatError.message}
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onInput={(e) => setInputValue((e.target as HTMLInputElement).value)}
              className="flex-1 px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder={isConnected ? 'Type a message...' : 'Connecting...'}
              disabled={!isConnected || chatLoading}
            />
            <button
              type="submit"
              disabled={!isConnected || chatLoading || !inputValue.trim()}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
            >
              {chatLoading ? 'Sending...' : 'Send'}
            </button>
            {messages.length > 0 && (
              <button
                type="button"
                data-testid="clear-btn"
                onClick={clearMessages}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
              >
                Clear
              </button>
            )}
          </form>
        </div>
      </div>
    </div>
  )
}

interface MessageBubbleProps {
  message: McpMessage
}

const MessageBubble: FunctionComponent<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user'
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-lg p-3 ${
          isUser
            ? 'bg-blue-500 text-white'
            : 'bg-gray-100 text-gray-800'
        }`}
      >
        <div className={isUser ? 'text-white' : 'text-gray-800'}>
          {message.content}
        </div>
        {message.toolResult && message.toolResult.length > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-200">
            <McpToolRenderer content={message.toolResult} />
          </div>
        )}
      </div>
    </div>
  )
}

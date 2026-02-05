import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent, cleanup } from '@testing-library/preact'
import { McpChat } from '../../src/pages/McpChat'

// Test constants
const CONNECTION_ERROR = 'Connection failed'
const USER_MESSAGE = 'Hello assistant'
const ASSISTANT_RESPONSE = 'Hello! How can I help you?'

// Hoist mock functions
const { 
  mockConnect,
  mockCallTool, 
  mockAddMessage,
  mockClearMessages,
} = vi.hoisted(() => ({
  mockConnect: vi.fn().mockResolvedValue(undefined),
  mockCallTool: vi.fn().mockResolvedValue(undefined),
  mockAddMessage: vi.fn(),
  mockClearMessages: vi.fn(),
}))

// Mock connection state
let mockIsConnected = false
let mockIsLoading = false
let mockConnectionError: Error | null = null
let mockMessages: Array<{ id: string; role: string; content: string }> = []
let mockChatLoading = false

vi.mock('../../src/hooks/useMcpConnection', () => ({
  useMcpConnection: () => ({
    isConnected: mockIsConnected,
    isLoading: mockIsLoading,
    error: mockConnectionError,
    tools: [],
    connect: mockConnect,
    disconnect: vi.fn(),
  }),
}))

vi.mock('../../src/hooks/useMcpChat', () => ({
  useMcpChat: () => ({
    messages: mockMessages,
    isLoading: mockChatLoading,
    error: null,
    addMessage: mockAddMessage,
    callTool: mockCallTool,
    clearMessages: mockClearMessages,
  }),
}))

describe('McpChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockIsConnected = false
    mockIsLoading = false
    mockConnectionError = null
    mockMessages = []
    mockChatLoading = false
  })

  afterEach(() => {
    cleanup()
  })

  describe('connection status', () => {
    it('shows connecting status when loading', () => {
      mockIsLoading = true
      
      const { container } = render(<McpChat />)
      
      expect(container.textContent).toContain('Connecting')
    })

    it('shows connected status when connected', () => {
      mockIsConnected = true
      
      const { container } = render(<McpChat />)
      
      expect(container.textContent).toContain('Connected')
    })

    it('shows disconnected status when not connected', () => {
      mockIsConnected = false
      
      const { container } = render(<McpChat />)
      
      expect(container.textContent).toContain('Disconnected')
    })

    it('displays connection error', () => {
      mockConnectionError = new Error(CONNECTION_ERROR)
      
      const { container } = render(<McpChat />)
      
      expect(container.textContent).toContain(CONNECTION_ERROR)
    })

    it('auto-connects on mount', () => {
      render(<McpChat />)
      
      expect(mockConnect).toHaveBeenCalled()
    })
  })

  describe('chat functionality', () => {
    it('displays messages', () => {
      mockIsConnected = true
      mockMessages = [
        { id: '1', role: 'user', content: USER_MESSAGE },
        { id: '2', role: 'assistant', content: ASSISTANT_RESPONSE },
      ]
      
      const { container } = render(<McpChat />)
      
      expect(container.textContent).toContain(USER_MESSAGE)
      expect(container.textContent).toContain(ASSISTANT_RESPONSE)
    })

    it('clears messages when clear button clicked', () => {
      mockIsConnected = true
      mockMessages = [{ id: '1', role: 'user', content: 'Test' }]
      
      const { container } = render(<McpChat />)
      
      const clearBtn = container.querySelector('[data-testid="clear-btn"]')
      expect(clearBtn).not.toBeNull()
      fireEvent.click(clearBtn!)
      
      expect(mockClearMessages).toHaveBeenCalled()
    })

    it('shows empty state when no messages', () => {
      mockIsConnected = true
      mockMessages = []
      
      const { container } = render(<McpChat />)
      
      expect(container.textContent).toContain('Send a message to start chatting')
    })
  })

  describe('message input', () => {
    it('has input field', () => {
      mockIsConnected = true
      
      const { container } = render(<McpChat />)
      
      const input = container.querySelector('input[type="text"]')
      expect(input).not.toBeNull()
    })

    it('enables input when connected', () => {
      mockIsConnected = true
      
      const { container } = render(<McpChat />)
      
      const input = container.querySelector('input[type="text"]') as HTMLInputElement
      expect(input.disabled).toBe(false)
    })

    it('disables input when not connected', () => {
      mockIsConnected = false
      
      const { container } = render(<McpChat />)
      
      const input = container.querySelector('input[type="text"]') as HTMLInputElement
      expect(input.disabled).toBe(true)
    })

    it('calls callTool with AGUIAssistant when form submitted', async () => {
      mockIsConnected = true
      
      const { container } = render(<McpChat />)
      
      const input = container.querySelector('input[type="text"]') as HTMLInputElement
      const form = container.querySelector('form') as HTMLFormElement
      
      fireEvent.input(input, { target: { value: USER_MESSAGE } })
      fireEvent.submit(form)
      
      expect(mockAddMessage).toHaveBeenCalledWith('user', USER_MESSAGE)
      expect(mockCallTool).toHaveBeenCalledWith('AGUIAssistant', { task: USER_MESSAGE })
    })

    it('shows sending state during tool call', () => {
      mockIsConnected = true
      mockChatLoading = true
      
      const { container } = render(<McpChat />)
      
      const sendBtn = container.querySelector('button[type="submit"]')
      expect(sendBtn?.textContent).toContain('Sending')
    })
  })

  describe('header', () => {
    it('displays page title', () => {
      const { container } = render(<McpChat />)
      
      expect(container.textContent).toContain('MCP Chat')
    })

    it('displays agent name', () => {
      const { container } = render(<McpChat />)
      
      expect(container.textContent).toContain('AGUIAssistant')
    })
  })
})

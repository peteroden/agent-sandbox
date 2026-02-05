import { render } from '@testing-library/preact'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ComponentChildren } from 'preact'
import { Chat } from '../../src/pages/Chat'
import { TestDefaults } from '../test-constants'

// Mock useChat to capture calls - must be defined before vi.mock for hoisting
const mockUseChat = vi.fn()

vi.mock('../../src/hooks/useChat', () => ({
  useChat: (options: { url: string }) => mockUseChat(options),
}))

// Mock logger - inline to avoid hoisting issues
const mockLoggerInfo = vi.fn()
vi.mock('@agent-sandbox/otel-web-sdk', () => ({
  logger: {
    debug: vi.fn(),
    info: (...args: unknown[]) => mockLoggerInfo(...args),
    warn: vi.fn(),
    error: vi.fn(),
  },
}))

// Mock react-ag-ui components
vi.mock('react-ag-ui', () => ({
  ChatProvider: ({ children }: { children: ComponentChildren }) => <div data-testid="chat-provider">{children}</div>,
  ChatHeader: () => <div data-testid="chat-header">Agent Chat</div>,
  MessageList: () => <div data-testid="message-list" />,
  MessageInput: () => <div data-testid="message-input" />,
}))

// Mock styles import
vi.mock('react-ag-ui/dist/styles.css', () => ({}))

// Mock agent returned by useChat
const mockAgent = {
  url: TestDefaults.AG_UI_URL,
  subscribe: () => ({ unsubscribe: () => {} }),
  addMessage: () => {},
  setMessages: () => {},
  runAgent: () => Promise.resolve({}),
}

describe('Chat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Set up mockUseChat return value
    mockUseChat.mockReturnValue({
      agent: mockAgent,
      messages: [],
      isLoading: false,
      error: null,
      sendMessage: vi.fn(),
      clearMessages: vi.fn(),
      addToolResult: vi.fn(),
    })
  })

  describe('useChat integration', () => {
    it('calls useChat with correct URL from environment', () => {
      render(<Chat />)

      expect(mockUseChat).toHaveBeenCalledWith({
        url: TestDefaults.AG_UI_URL,
      })
    })

    it('calls useChat exactly once on render', () => {
      render(<Chat />)

      expect(mockUseChat).toHaveBeenCalledTimes(1)
    })
  })

  describe('logging', () => {
    it('logs Chat page loaded on mount with agent URL', () => {
      render(<Chat />)

      expect(mockLoggerInfo).toHaveBeenCalledWith('Chat page loaded', {
        'agent.url': TestDefaults.AG_UI_URL,
      })
    })
  })

  describe('component rendering', () => {
    it('renders ChatProvider component', () => {
      const { container } = render(<Chat />)
      expect(container.querySelector('[data-testid="chat-provider"]')).not.toBeNull()
    })

    it('renders ChatHeader component', () => {
      const { container } = render(<Chat />)
      expect(container.querySelector('[data-testid="chat-header"]')).not.toBeNull()
    })

    it('renders MessageList component', () => {
      const { container } = render(<Chat />)
      expect(container.querySelector('[data-testid="message-list"]')).not.toBeNull()
    })

    it('renders MessageInput component', () => {
      const { container } = render(<Chat />)
      expect(container.querySelector('[data-testid="message-input"]')).not.toBeNull()
    })
  })
})

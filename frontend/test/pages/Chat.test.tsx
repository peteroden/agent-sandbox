import { render } from '@testing-library/preact'
import { describe, it, expect, vi } from 'vitest'
import type { ComponentChildren } from 'preact'
import { Chat } from '../../src/pages/Chat'

// Mock telemetry
vi.mock('../../src/services/telemetry', () => ({
  getTracer: () => ({
    startSpan: vi.fn(() => ({
      setAttribute: vi.fn(),
      setStatus: vi.fn(),
      recordException: vi.fn(),
      end: vi.fn(),
    })),
  }),
  startSpan: vi.fn(() => ({ end: vi.fn(), addEvent: vi.fn() })),
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
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

// Mock @ag-ui/client
vi.mock('@ag-ui/client', () => ({
  HttpAgent: class {
    constructor(_config: { url: string; description?: string }) {}
    subscribe = () => ({ unsubscribe: () => {} })
    addMessage = () => {}
    setMessages = () => {}
    runAgent = () => Promise.resolve({})
  },
}))

describe('Chat', () => {
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

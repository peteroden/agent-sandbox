import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/preact'
import { McpAppHost } from '../../src/components/McpAppHost'

// Test constants
const HTML_CONTENT = '<html><body><h1>Test View</h1></body></html>'
const RESOURCE_URI = 'ui://demo-app/view.html'
const INITIAL_DATA = { cpu_percent: 25.0, memory_percent: 60.0 }
const TOOL_NAME = 'system_stats'
const TOOL_ARGS = { verbose: true }

// Mock bridge instance
const mockBridge = {
  oncalltool: null as ((params: Record<string, unknown>) => Promise<unknown>) | null,
  oninitialized: null as (() => void) | null,
  connect: vi.fn().mockResolvedValue(undefined),
  sendToolResult: vi.fn(),
  teardownResource: vi.fn().mockResolvedValue(undefined),
}

vi.mock('@modelcontextprotocol/ext-apps/app-bridge', () => {
  function FakeAppBridge() {
    mockBridge.oncalltool = null
    mockBridge.oninitialized = null
    return mockBridge
  }
  function FakePostMessageTransport() {
    return { _mock: true }
  }
  return {
    AppBridge: FakeAppBridge,
    PostMessageTransport: FakePostMessageTransport,
  }
})

const mockCallTool = vi.fn()
vi.mock('../../src/services/mcpClient', () => ({
  mcpClient: { callTool: (...args: unknown[]) => mockCallTool(...args) },
}))

describe('McpAppHost', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockBridge.oncalltool = null
    mockBridge.oninitialized = null
  })

  describe('iframe rendering', () => {
    it('renders iframe with srcDoc and sandbox', () => {
      const { container } = render(
        <McpAppHost htmlContent={HTML_CONTENT} uri={RESOURCE_URI} />
      )

      const iframe = container.querySelector('iframe')
      expect(iframe).not.toBeNull()
      expect(iframe?.getAttribute('sandbox')).toBe('allow-scripts')
      expect(iframe?.getAttribute('srcdoc')).toBe(HTML_CONTENT)
    })

    it('renders with default styling', () => {
      const { container } = render(
        <McpAppHost htmlContent={HTML_CONTENT} uri={RESOURCE_URI} />
      )

      const iframe = container.querySelector('iframe') as HTMLIFrameElement
      expect(iframe.style.width).toBe('100%')
      expect(iframe.style.border).toContain('none')
    })
  })

  describe('bridge lifecycle', () => {
    it('sets up bridge on iframe load', () => {
      render(<McpAppHost htmlContent={HTML_CONTENT} uri={RESOURCE_URI} />)

      const iframe = document.querySelector('iframe')
      iframe?.dispatchEvent(new Event('load'))

      // Bridge should connect after iframe load
      expect(mockBridge.connect).toHaveBeenCalled()
    })

    it('sets oncalltool handler on bridge', () => {
      render(<McpAppHost htmlContent={HTML_CONTENT} uri={RESOURCE_URI} />)

      const iframe = document.querySelector('iframe')
      iframe?.dispatchEvent(new Event('load'))

      expect(mockBridge.oncalltool).toBeTypeOf('function')
    })
  })

  describe('tool call proxying', () => {
    it('proxies oncalltool to mcpClient.callTool', async () => {
      const toolResult = [{ type: 'text', text: '{"result": "ok"}' }]
      mockCallTool.mockResolvedValue(toolResult)

      render(<McpAppHost htmlContent={HTML_CONTENT} uri={RESOURCE_URI} />)

      const iframe = document.querySelector('iframe')
      iframe?.dispatchEvent(new Event('load'))

      // oncalltool handler should be set
      expect(mockBridge.oncalltool).toBeTypeOf('function')

      // Simulate tool call from iframe
      const result = await mockBridge.oncalltool!({ name: TOOL_NAME, arguments: TOOL_ARGS })

      expect(mockCallTool).toHaveBeenCalledWith(TOOL_NAME, TOOL_ARGS)
      expect(result).toEqual({
        content: [{ type: 'text', text: '{"result": "ok"}' }],
      })
    })

    it('handles missing arguments in tool call', async () => {
      mockCallTool.mockResolvedValue([{ type: 'text', text: 'ok' }])

      render(<McpAppHost htmlContent={HTML_CONTENT} uri={RESOURCE_URI} />)

      const iframe = document.querySelector('iframe')
      iframe?.dispatchEvent(new Event('load'))

      await mockBridge.oncalltool!({ name: TOOL_NAME })

      expect(mockCallTool).toHaveBeenCalledWith(TOOL_NAME, {})
    })
  })

  describe('initial data injection', () => {
    it('sends tool result with initial data on bridge initialized', () => {
      render(
        <McpAppHost htmlContent={HTML_CONTENT} uri={RESOURCE_URI} initialData={INITIAL_DATA} />
      )

      const iframe = document.querySelector('iframe')
      iframe?.dispatchEvent(new Event('load'))

      // Trigger oninitialized callback
      expect(mockBridge.oninitialized).toBeTypeOf('function')
      mockBridge.oninitialized!()

      expect(mockBridge.sendToolResult).toHaveBeenCalledWith({
        content: [{ type: 'text', text: JSON.stringify(INITIAL_DATA) }],
        structuredContent: INITIAL_DATA,
      })
    })

    it('skips sendToolResult when no initial data', () => {
      render(<McpAppHost htmlContent={HTML_CONTENT} uri={RESOURCE_URI} />)

      const iframe = document.querySelector('iframe')
      iframe?.dispatchEvent(new Event('load'))

      mockBridge.oninitialized!()

      expect(mockBridge.sendToolResult).not.toHaveBeenCalled()
    })
  })
})

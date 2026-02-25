import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/preact'
import { McpAppDemo } from '../../src/pages/McpAppDemo'

// Mock UIResourceRenderer
vi.mock('@mcp-ui/client', () => ({
  UIResourceRenderer: (props: Record<string, unknown>) => {
    const resource = props.resource as Record<string, string>
    return (
      <div data-testid="ui-resource-renderer" data-uri={resource?.uri}>
        {resource?.text}
      </div>
    )
  },
}))

const TOOL_NAME = 'system_stats'
const TOOL_DESCRIPTION = 'Get system stats'
const RESOURCE_URI = 'ui://demo-app/view.html'
const RESOURCE_HTML = '<html><body>Stats View</body></html>'
const TOOL_RESULT_TEXT = '{"cpu": 25.0}'

const mockConnect = vi.fn()
const mockListTools = vi.fn()
const mockCallTool = vi.fn()
let mockIsConnected = false

vi.mock('../../src/services/mcpClient', () => ({
  mcpClient: {
    get isConnected() { return mockIsConnected },
    connect: (...args: unknown[]) => {
      mockIsConnected = true
      return mockConnect(...args)
    },
    listTools: () => mockListTools(),
    callTool: (...args: unknown[]) => mockCallTool(...args),
  },
}))

describe('McpAppDemo', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockIsConnected = false
    mockConnect.mockResolvedValue(undefined)
    mockListTools.mockResolvedValue([])
    mockCallTool.mockResolvedValue([])
    vi.stubGlobal('fetch', vi.fn())
  })

  it('connects on mount and shows connected status', async () => {
    mockListTools.mockResolvedValue([
      { name: TOOL_NAME, description: TOOL_DESCRIPTION },
    ])

    const { getByText } = render(<McpAppDemo />)

    await waitFor(() => {
      expect(getByText('Connected')).toBeTruthy()
    })
    expect(mockConnect).toHaveBeenCalled()
  })

  it('displays tools with interactive view indicator', async () => {
    mockListTools.mockResolvedValue([
      {
        name: TOOL_NAME,
        description: TOOL_DESCRIPTION,
        _meta: { ui: { resourceUri: RESOURCE_URI } },
      },
    ])

    const { getByText } = render(<McpAppDemo />)

    await waitFor(() => {
      expect(getByText(TOOL_NAME)).toBeTruthy()
      expect(getByText('Has interactive view')).toBeTruthy()
    })
  })

  it('calls tool and fetches resource HTML via backend proxy', async () => {
    mockListTools.mockResolvedValue([
      {
        name: TOOL_NAME,
        _meta: { ui: { resourceUri: RESOURCE_URI } },
      },
    ])
    mockCallTool.mockResolvedValue([
      { type: 'text', text: TOOL_RESULT_TEXT },
    ])
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      text: () => Promise.resolve(RESOURCE_HTML),
    } as Response)

    const { getByText, container } = render(<McpAppDemo />)

    await waitFor(() => {
      expect(getByText('Run')).toBeTruthy()
    })

    getByText('Run').click()

    await waitFor(() => {
      expect(mockCallTool).toHaveBeenCalledWith(TOOL_NAME, {})
      expect(fetch).toHaveBeenCalledWith(
        `/api/mcp-resource?uri=${encodeURIComponent(RESOURCE_URI)}`,
      )
      const renderer = container.querySelector('[data-testid="ui-resource-renderer"]')
      expect(renderer).not.toBeNull()
      expect(renderer?.getAttribute('data-uri')).toBe(RESOURCE_URI)
    })
  })

  it('shows error on connection failure', async () => {
    mockConnect.mockRejectedValue(new Error('Connection refused'))

    const { getByText } = render(<McpAppDemo />)

    await waitFor(() => {
      expect(getByText('Error: Connection refused')).toBeTruthy()
    })
  })
})

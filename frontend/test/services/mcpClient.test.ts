import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { McpClientService, type Tool, type CallToolResult } from '../../src/services/mcpClient'
import { TestDefaults } from '../test-constants'

// Test constants
const TOOL_ONE = 'tool-one'
const TOOL_TWO = 'tool-two'
const TOOL_DESCRIPTION = 'A test tool'
const CONNECTION_ERROR = 'Connection failed'
const NOT_CONNECTED_ERROR = 'Not connected'

// Hoist mock functions
const { mockConnect, mockClose, mockListTools, mockCallTool, mockReadResource } = vi.hoisted(() => {
  return {
    mockConnect: vi.fn().mockResolvedValue(undefined),
    mockClose: vi.fn().mockResolvedValue(undefined),
    mockListTools: vi.fn().mockResolvedValue({ tools: [] }),
    mockCallTool: vi.fn().mockResolvedValue({ content: [] }),
    mockReadResource: vi.fn().mockResolvedValue({ contents: [] }),
  }
})

// Mock MCP SDK using class-based mocks for proper constructor behavior
vi.mock('@modelcontextprotocol/sdk/client/index.js', () => ({
  Client: class MockClient {
    connect = mockConnect
    close = mockClose
    listTools = mockListTools
    callTool = mockCallTool
    readResource = mockReadResource
  },
}))

vi.mock('@modelcontextprotocol/sdk/client/streamablehttp.js', () => ({
  StreamableHTTPClientTransport: class MockTransport {
    constructor(_url: URL) {}
  },
}))

describe('McpClientService', () => {
  let service: McpClientService

  beforeEach(() => {
    vi.clearAllMocks()
    service = new McpClientService()
  })

  afterEach(async () => {
    if (service.isConnected) {
      await service.disconnect()
    }
  })

  describe('connect', () => {
    it('establishes connection to MCP server', async () => {
      await service.connect(TestDefaults.MCP_URL)

      expect(mockConnect).toHaveBeenCalled()
      expect(service.isConnected).toBe(true)
    })

    it('propagates connection errors', async () => {
      mockConnect.mockRejectedValueOnce(new Error(CONNECTION_ERROR))

      await expect(service.connect(TestDefaults.MCP_URL)).rejects.toThrow(CONNECTION_ERROR)
      expect(service.isConnected).toBe(false)
    })

    it('disconnects existing connection before reconnecting', async () => {
      await service.connect(TestDefaults.MCP_URL)
      await service.connect(TestDefaults.MCP_URL_CUSTOM)

      expect(mockClose).toHaveBeenCalledTimes(1)
      expect(mockConnect).toHaveBeenCalledTimes(2)
    })
  })

  describe('disconnect', () => {
    it('closes the connection', async () => {
      await service.connect(TestDefaults.MCP_URL)
      await service.disconnect()

      expect(mockClose).toHaveBeenCalled()
      expect(service.isConnected).toBe(false)
    })

    it('does nothing when not connected', async () => {
      await service.disconnect()

      expect(mockClose).not.toHaveBeenCalled()
    })
  })

  describe('listTools', () => {
    it('returns available tools from server', async () => {
      const mockTools: Tool[] = [
        { name: TOOL_ONE, description: TOOL_DESCRIPTION },
        { name: TOOL_TWO },
      ]
      mockListTools.mockResolvedValueOnce({ tools: mockTools })

      await service.connect(TestDefaults.MCP_URL)
      const tools = await service.listTools()

      expect(tools).toEqual(mockTools)
    })

    it('preserves _meta on tools', async () => {
      const mockTools: Tool[] = [
        {
          name: TOOL_ONE,
          _meta: { ui: { resourceUri: 'ui://demo/view.html' } },
        },
      ]
      mockListTools.mockResolvedValueOnce({ tools: mockTools })

      await service.connect(TestDefaults.MCP_URL)
      const tools = await service.listTools()

      expect(tools[0]._meta).toEqual({ ui: { resourceUri: 'ui://demo/view.html' } })
    })

    it('throws when not connected', async () => {
      await expect(service.listTools()).rejects.toThrow(NOT_CONNECTED_ERROR)
    })
  })

  describe('callTool', () => {
    it('invokes tool and returns result', async () => {
      const mockResult: CallToolResult = {
        content: [{ type: 'text', text: 'Tool output' }],
      }
      mockCallTool.mockResolvedValueOnce(mockResult)

      await service.connect(TestDefaults.MCP_URL)
      const result = await service.callTool(TOOL_ONE, { arg: 'value' })

      expect(mockCallTool).toHaveBeenCalledWith({ name: TOOL_ONE, arguments: { arg: 'value' } })
      expect(result).toEqual(mockResult.content)
    })

    it('throws when not connected', async () => {
      await expect(service.callTool(TOOL_ONE, {})).rejects.toThrow(NOT_CONNECTED_ERROR)
    })
  })

  describe('readResource', () => {
    const RESOURCE_URI = 'ui://demo/view.html'
    const RESOURCE_HTML = '<html><body>Hello</body></html>'

    it('reads resource content from server', async () => {
      mockReadResource.mockResolvedValueOnce({
        contents: [{ uri: RESOURCE_URI, text: RESOURCE_HTML }],
      })

      await service.connect(TestDefaults.MCP_URL)
      const content = await service.readResource(RESOURCE_URI)

      expect(mockReadResource).toHaveBeenCalledWith({ uri: RESOURCE_URI })
      expect(content).toBe(RESOURCE_HTML)
    })

    it('throws when resource has no text content', async () => {
      mockReadResource.mockResolvedValueOnce({ contents: [] })

      await service.connect(TestDefaults.MCP_URL)

      await expect(service.readResource(RESOURCE_URI)).rejects.toThrow(
        `Resource not found: ${RESOURCE_URI}`,
      )
    })

    it('throws when not connected', async () => {
      await expect(service.readResource(RESOURCE_URI)).rejects.toThrow(NOT_CONNECTED_ERROR)
    })
  })

  describe('isConnected', () => {
    it('returns false initially', () => {
      expect(service.isConnected).toBe(false)
    })

    it('returns true after connecting', async () => {
      await service.connect(TestDefaults.MCP_URL)
      expect(service.isConnected).toBe(true)
    })

    it('returns false after disconnecting', async () => {
      await service.connect(TestDefaults.MCP_URL)
      await service.disconnect()
      expect(service.isConnected).toBe(false)
    })
  })
})

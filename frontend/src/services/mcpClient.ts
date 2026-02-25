import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamablehttp.js'

/**
 * Represents a tool available from the MCP server
 */
export interface Tool {
  name: string
  description?: string
  inputSchema?: Record<string, unknown>
  _meta?: Record<string, unknown>
}

/**
 * Content item in a tool call result
 */
export interface ContentItem {
  type: string
  text?: string
  blob?: string
  mimeType?: string
  uri?: string
  htmlContent?: string
}

/**
 * Result of calling a tool
 */
export interface CallToolResult {
  content: ContentItem[]
  isError?: boolean
}

/**
 * MCP client service for connecting to and interacting with MCP servers.
 * Provides methods to list available tools and invoke them.
 */
export class McpClientService {
  private client: Client | null = null
  private transport: StreamableHTTPClientTransport | null = null

  /**
   * Connects to an MCP server at the given URL.
   * Disconnects any existing connection first.
   * 
   * @param url - The URL of the MCP server endpoint
   */
  async connect(url: string): Promise<void> {
    // Disconnect existing connection if any
    if (this.client) {
      await this.disconnect()
    }

    try {
      this.transport = new StreamableHTTPClientTransport(
        new URL(url, window.location.origin)
      )
      this.client = new Client(
        { name: 'agent-sandbox-ui', version: '1.0.0' },
        {}
      )
      await this.client.connect(this.transport)
    } catch (error) {
      this.client = null
      this.transport = null
      throw error
    }
  }

  /**
   * Disconnects from the current MCP server.
   */
  async disconnect(): Promise<void> {
    if (this.client) {
      await this.client.close()
      this.client = null
      this.transport = null
    }
  }

  /**
   * Lists all available tools from the connected MCP server.
   * 
   * @returns Array of available tools
   * @throws Error if not connected
   */
  async listTools(): Promise<Tool[]> {
    if (!this.client) {
      throw new Error('Not connected')
    }
    const result = await this.client.listTools()
    return result.tools
  }

  /**
   * Calls a tool on the connected MCP server.
   * 
   * @param name - The name of the tool to call
   * @param args - Arguments to pass to the tool
   * @returns The tool's result content
   * @throws Error if not connected
   */
  async callTool(name: string, args: Record<string, unknown>): Promise<ContentItem[]> {
    if (!this.client) {
      throw new Error('Not connected')
    }
    const result = await this.client.callTool({ name, arguments: args })
    return result.content as ContentItem[]
  }

  /**
   * Reads a resource from the connected MCP server.
   *
   * @param uri - The resource URI to read
   * @returns The resource text content
   * @throws Error if not connected or resource not found
   */
  async readResource(uri: string): Promise<string> {
    if (!this.client) {
      throw new Error('Not connected')
    }
    const result = await this.client.readResource({ uri })
    const content = result.contents[0]
    if (!content || !('text' in content)) {
      throw new Error(`Resource not found: ${uri}`)
    }
    return content.text
  }

  /**
   * Whether the client is currently connected to a server.
   */
  get isConnected(): boolean {
    return this.client !== null
  }
}

/**
 * Singleton instance of the MCP client service
 */
export const mcpClient = new McpClientService()

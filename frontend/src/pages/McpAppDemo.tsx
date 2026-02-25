import { useState, useEffect, useCallback } from 'preact/hooks'
import type { FunctionComponent } from 'preact'
import { mcpClient, type Tool, type ContentItem } from '../services/mcpClient'
import { McpToolRenderer } from '../components/McpToolRenderer'

/**
 * Extracts the ui:// resource URI from a tool's _meta, if present.
 */
function getResourceUri(tool: Tool): string | undefined {
  const meta = tool._meta as Record<string, Record<string, string>> | undefined
  return meta?.ui?.resourceUri
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
 * MCP App Demo page - demonstrates MCP Apps with interactive HTML views.
 * Connects to the main AG-UI server and renders tool results
 * alongside their associated HTML views in sandboxed iframes.
 */
export const McpAppDemo: FunctionComponent = () => {
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tools, setTools] = useState<Tool[]>([])
  const [toolResult, setToolResult] = useState<ContentItem[] | null>(null)

  const connect = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      if (!mcpClient.isConnected) {
        await mcpClient.connect('/mcp')
      }
      setIsConnected(true)
      const availableTools = await mcpClient.listTools()
      setTools(availableTools)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setIsLoading(false)
    }
  }, [])

  const callToolWithView = useCallback(async (tool: Tool) => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await mcpClient.callTool(tool.name, {})

      const resourceUri = getResourceUri(tool)
      if (resourceUri) {
        const html = await fetchResourceHtml(resourceUri)
        result.push({ type: 'resource', uri: resourceUri, htmlContent: html })
      }

      setToolResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    connect()
  }, [connect])

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-4">
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-800">MCP App Demo</h1>
            <p className="text-sm text-gray-500">
              Interactive HTML views from MCP tool servers
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`w-3 h-3 rounded-full ${
                isConnected ? 'bg-green-500' : isLoading ? 'bg-yellow-500' : 'bg-red-500'
              }`}
            />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : isLoading ? 'Connecting...' : 'Disconnected'}
            </span>
          </div>
        </div>
        {error && (
          <div className="text-red-600 text-sm mt-2">Error: {error}</div>
        )}
      </div>

      {isConnected && tools.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold text-gray-700 mb-3">Available Tools</h2>
          <div className="space-y-2">
            {tools.map((tool) => {
              const hasView = !!getResourceUri(tool)
              return (
                <div key={tool.name} className="flex items-center justify-between p-3 bg-gray-50 rounded border">
                  <div>
                    <span className="font-medium text-gray-800">{tool.name}</span>
                    {tool.description && (
                      <p className="text-sm text-gray-500">{tool.description}</p>
                    )}
                    {hasView && (
                      <span className="text-xs text-blue-600">Has interactive view</span>
                    )}
                  </div>
                  <button
                    onClick={() => callToolWithView(tool)}
                    disabled={isLoading}
                    className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50"
                  >
                    {isLoading ? 'Running...' : 'Run'}
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {toolResult && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold text-gray-700 mb-3">Result</h2>
          <McpToolRenderer content={toolResult} />
        </div>
      )}
    </div>
  )
}

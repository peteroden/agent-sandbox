import type { FunctionComponent } from 'preact'
import { useCallback } from 'preact/hooks'
import { UIResourceRenderer } from '@mcp-ui/client'
import { mcpClient, type ContentItem } from '../services/mcpClient'

interface McpToolRendererProps {
  /** The content items to render */
  content: ContentItem[]
  /** Whether this is an error result */
  isError?: boolean
  /** Callback when user interacts with UI elements */
  onAction?: (action: { type: string; payload?: unknown }) => void
}

/**
 * Renders MCP tool call results.
 * Handles text content, and uses UIResourceRenderer from @mcp-ui/client
 * for MCP App HTML views with full protocol support.
 */
/**
 * Extracts the first valid JSON object from text content.
 */
function extractJson(text: string): Record<string, unknown> | null {
  const start = text.indexOf('{')
  if (start === -1) return null
  let depth = 0
  for (let i = start; i < text.length; i++) {
    if (text[i] === '{') depth++
    else if (text[i] === '}') depth--
    if (depth === 0) {
      try {
        return JSON.parse(text.slice(start, i + 1))
      } catch {
        return null
      }
    }
  }
  return null
}

export const McpToolRenderer: FunctionComponent<McpToolRendererProps> = ({
  content,
  isError = false,
  onAction,
}) => {
  if (content.length === 0) {
    return <div />
  }

  // Collect JSON from text items to inject as initial render data for MCP App views
  const textContent = content
    .filter(item => item.type === 'text' && item.text)
    .map(item => item.text!)
    .join('\n')
  const renderData = extractJson(textContent)

  return (
    <div
      className={`mcp-tool-result space-y-2 ${isError ? 'border-l-4 border-red-500 pl-2' : ''}`}
      data-error={isError || undefined}
    >
      {content.map((item, index) => (
        <ToolContentItem key={index} item={item} renderData={renderData} onAction={onAction} />
      ))}
    </div>
  )
}

interface ToolContentItemProps {
  item: ContentItem
  renderData?: Record<string, unknown> | null
  onAction?: (action: { type: string; payload?: unknown }) => void
}

const ToolContentItem: FunctionComponent<ToolContentItemProps> = ({ item, renderData }) => {
  const handleUIAction = useCallback(async (result: Record<string, unknown>) => {
    const method = result.method as string | undefined
    if (method === 'tools/call') {
      const params = result.params as { name: string; arguments?: Record<string, unknown> }
      const toolResult = await mcpClient.callTool(params.name, params.arguments ?? {})
      return { content: toolResult }
    }
  }, [])

  // Handle text content
  if (item.type === 'text' && item.text) {
    return (
      <pre className="whitespace-pre-wrap break-all text-sm bg-gray-50 p-2 rounded border border-gray-200">
        {item.text}
      </pre>
    )
  }

  // Handle MCP App HTML views via UIResourceRenderer
  if (item.htmlContent && item.uri) {
    return (
      <div className="mcp-app-view rounded border border-gray-200 overflow-hidden">
        <UIResourceRenderer
          resource={{ uri: item.uri, text: item.htmlContent, mimeType: 'text/html' }}
          onUIAction={handleUIAction}
          htmlProps={{
            iframeRenderData: renderData ?? undefined,
            autoResizeIframe: true,
            style: { width: '100%', minHeight: '300px', border: 'none' },
          }}
        />
      </div>
    )
  }

  // Handle UI resources without fetched content
  if (item.uri?.startsWith('ui://')) {
    return (
      <div className="bg-blue-50 p-2 rounded border border-blue-200">
        <span className="text-sm text-blue-700">UI Component: {item.uri}</span>
      </div>
    )
  }

  // Handle other content types with a basic fallback
  return (
    <div className="bg-gray-100 p-2 rounded border border-gray-300">
      <span className="text-sm text-gray-600">[{item.type}]</span>
      {item.uri && <span className="text-xs text-gray-500 ml-2">{item.uri}</span>}
      {item.mimeType && <span className="text-xs text-gray-500 ml-2">({item.mimeType})</span>}
    </div>
  )
}

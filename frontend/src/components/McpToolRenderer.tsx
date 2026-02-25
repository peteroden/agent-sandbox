import type { FunctionComponent } from 'preact'
import type { ContentItem } from '../services/mcpClient'

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
 * Handles text content, and provides extension points for UI resources.
 */
export const McpToolRenderer: FunctionComponent<McpToolRendererProps> = ({
  content,
  isError = false,
  onAction,
}) => {
  if (content.length === 0) {
    return <div />
  }

  return (
    <div
      className={`mcp-tool-result space-y-2 ${isError ? 'border-l-4 border-red-500 pl-2' : ''}`}
      data-error={isError || undefined}
    >
      {content.map((item, index) => (
        <ToolContentItem key={index} item={item} onAction={onAction} />
      ))}
    </div>
  )
}

interface ToolContentItemProps {
  item: ContentItem
  onAction?: (action: { type: string; payload?: unknown }) => void
}

const ToolContentItem: FunctionComponent<ToolContentItemProps> = ({ item }) => {
  // Handle text content
  if (item.type === 'text' && item.text) {
    return (
      <pre className="whitespace-pre-wrap break-all text-sm bg-gray-50 p-2 rounded border border-gray-200">
        {item.text}
      </pre>
    )
  }

  // Handle HTML content from MCP App resources
  if (item.htmlContent) {
    return (
      <div className="mcp-app-view rounded border border-gray-200 overflow-hidden">
        <iframe
          srcDoc={item.htmlContent}
          sandbox="allow-scripts"
          title="MCP App View"
          className="w-full border-0"
          style={{ minHeight: '300px' }}
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

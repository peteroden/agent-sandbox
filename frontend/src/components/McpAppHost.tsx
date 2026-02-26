import type { FunctionComponent } from 'preact'
import { useRef, useEffect, useCallback } from 'preact/hooks'
import { AppBridge, PostMessageTransport } from '@modelcontextprotocol/ext-apps/app-bridge'
import { mcpClient, type ContentItem } from '../services/mcpClient'

interface McpAppHostProps {
  htmlContent: string
  uri: string
  initialData?: Record<string, unknown> | null
}

/**
 * Renders an MCP App view in an iframe using the ext-apps AppBridge protocol.
 *
 * Creates a sandboxed iframe with the HTML content and bridges JSON-RPC
 * postMessage communication between the iframe (App) and the MCP gateway
 * server via AppBridge.
 */
export const McpAppHost: FunctionComponent<McpAppHostProps> = ({
  htmlContent,
  initialData,
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const bridgeRef = useRef<AppBridge | null>(null)

  const setupBridge = useCallback(async () => {
    const iframe = iframeRef.current
    if (!iframe?.contentWindow || bridgeRef.current) return

    const bridge = new AppBridge(
      null,
      { name: 'AgentSandbox', version: '1.0.0' },
      { serverTools: {} },
    )

    bridge.oncalltool = async (params: { name: string; arguments?: Record<string, unknown> }) => {
      const items = await mcpClient.callTool(params.name, params.arguments ?? {})
      return {
        content: items
          .filter((item: ContentItem) => item.type === 'text' && item.text)
          .map((item: ContentItem) => ({ type: 'text' as const, text: item.text! })),
      }
    }

    bridge.oninitialized = () => {
      if (initialData) {
        bridge.sendToolResult({
          content: [{ type: 'text', text: JSON.stringify(initialData) }],
          structuredContent: initialData,
        })
      }
    }

    const transport = new PostMessageTransport(
      iframe.contentWindow,
      iframe.contentWindow,
    )

    await bridge.connect(transport)
    bridgeRef.current = bridge
  }, [initialData])

  useEffect(() => {
    return () => {
      if (bridgeRef.current) {
        bridgeRef.current.teardownResource({})
        bridgeRef.current = null
      }
    }
  }, [])

  return (
    <iframe
      ref={iframeRef}
      srcDoc={htmlContent}
      sandbox="allow-scripts"
      onLoad={setupBridge}
      style={{ width: '100%', minHeight: '300px', border: 'none' }}
    />
  )
}

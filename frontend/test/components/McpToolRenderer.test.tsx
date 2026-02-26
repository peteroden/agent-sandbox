import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/preact'
import { McpToolRenderer } from '../../src/components/McpToolRenderer'

// Mock McpAppHost since it wraps ext-apps AppBridge internals
vi.mock('../../src/components/McpAppHost', () => ({
  McpAppHost: (props: Record<string, unknown>) => {
    return (
      <div data-testid="mcp-app-host" data-uri={props.uri as string}>
        {props.htmlContent as string}
      </div>
    )
  },
}))

// Mock mcpClient
vi.mock('../../src/services/mcpClient', () => ({
  mcpClient: { callTool: vi.fn() },
}))

// Test constants
const TEXT_CONTENT = 'Tool output text'
const JSON_CONTENT = '{"result": "success"}'

describe('McpToolRenderer', () => {
  describe('text content', () => {
    it('renders text content in pre tag', () => {
      const content = [{ type: 'text', text: TEXT_CONTENT }]
      
      const { container } = render(<McpToolRenderer content={content} />)
      
      const preElement = container.querySelector('pre')
      expect(preElement).not.toBeNull()
      expect(preElement?.textContent).toBe(TEXT_CONTENT)
    })

    it('renders multiple text items', () => {
      const content = [
        { type: 'text', text: 'First line' },
        { type: 'text', text: 'Second line' },
      ]
      
      const { container } = render(<McpToolRenderer content={content} />)
      
      const preElements = container.querySelectorAll('pre')
      expect(preElements.length).toBe(2)
      expect(preElements[0].textContent).toBe('First line')
      expect(preElements[1].textContent).toBe('Second line')
    })
  })

  describe('JSON content', () => {
    it('renders JSON as formatted string', () => {
      const content = [{ type: 'text', text: JSON_CONTENT }]
      
      const { container } = render(<McpToolRenderer content={content} />)
      
      const preElement = container.querySelector('pre')
      expect(preElement?.textContent).toBe(JSON_CONTENT)
    })
  })

  describe('empty content', () => {
    it('renders empty div for empty array', () => {
      const { container } = render(<McpToolRenderer content={[]} />)
      
      const div = container.firstChild as HTMLDivElement
      expect(div.children.length).toBe(0)
    })
  })

  describe('unknown content type', () => {
    it('renders type label for non-text content', () => {
      const content = [{ type: 'image', uri: 'https://example.com/img.png' }]
      
      const { container } = render(<McpToolRenderer content={content} />)
      
      expect(container.textContent).toContain('[image]')
    })
  })

  describe('MCP App HTML content', () => {
    const HTML_CONTENT = '<html><body><h1>Stats Dashboard</h1></body></html>'
    const RESOURCE_URI = 'ui://demo-app/view.html'

    it('renders McpAppHost for htmlContent with uri', () => {
      const content = [{ type: 'resource', uri: RESOURCE_URI, htmlContent: HTML_CONTENT }]

      const { container } = render(<McpToolRenderer content={content} />)

      const host = container.querySelector('[data-testid="mcp-app-host"]')
      expect(host).not.toBeNull()
      expect(host?.getAttribute('data-uri')).toBe(RESOURCE_URI)
    })

    it('renders ui:// fallback label when no htmlContent', () => {
      const content = [{ type: 'resource', uri: 'ui://demo/view.html' }]

      const { container } = render(<McpToolRenderer content={content} />)

      expect(container.textContent).toContain('UI Component: ui://demo/view.html')
    })
  })

  describe('error content', () => {
    it('displays error indicator for error results', () => {
      const content = [{ type: 'text', text: 'Error message' }]
      
      const { container } = render(<McpToolRenderer content={content} isError />)
      
      const errorDiv = container.querySelector('[data-error]')
      expect(errorDiv).not.toBeNull()
      expect(container.textContent).toContain('Error message')
    })
  })
})

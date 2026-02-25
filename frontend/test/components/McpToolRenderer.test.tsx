import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/preact'
import { McpToolRenderer } from '../../src/components/McpToolRenderer'

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

    it('renders htmlContent in sandboxed iframe', () => {
      const content = [{ type: 'resource', htmlContent: HTML_CONTENT }]

      const { container } = render(<McpToolRenderer content={content} />)

      const iframe = container.querySelector('iframe')
      expect(iframe).not.toBeNull()
      expect(iframe?.getAttribute('srcdoc')).toBe(HTML_CONTENT)
      expect(iframe?.getAttribute('sandbox')).toBe('allow-scripts')
    })

    it('sets title on iframe for accessibility', () => {
      const content = [{ type: 'resource', htmlContent: HTML_CONTENT }]

      const { container } = render(<McpToolRenderer content={content} />)

      const iframe = container.querySelector('iframe')
      expect(iframe?.getAttribute('title')).toBe('MCP App View')
    })

    it('renders ui:// fallback label when no htmlContent', () => {
      const content = [{ type: 'resource', uri: 'ui://demo/view.html' }]

      const { container } = render(<McpToolRenderer content={content} />)

      expect(container.textContent).toContain('UI Component: ui://demo/view.html')
      expect(container.querySelector('iframe')).toBeNull()
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

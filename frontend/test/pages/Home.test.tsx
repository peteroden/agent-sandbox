import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/preact'
import { Home } from '../../src/pages/Home'

// Mock telemetry
vi.mock('../../src/services/telemetry', () => ({
  logger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}))

describe('Home component', () => {
  it('renders welcome message', () => {
    const { container } = render(<Home />)
    expect(container.textContent).toContain('Welcome to the frontend skeleton')
  })

  it('renders heading', () => {
    const { container } = render(<Home />)
    const h1 = container.querySelector('h1')
    expect(h1?.textContent).toBe('Home')
  })
})

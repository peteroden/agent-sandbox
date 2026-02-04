import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/preact'
import { Home } from '../../src/pages/Home'

// Local test constants
const HEADING_TEXT = 'Home'
const WELCOME_MESSAGE = 'Welcome to the frontend skeleton'

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
    expect(container.textContent).toContain(WELCOME_MESSAGE)
  })

  it('renders heading', () => {
    const { container } = render(<Home />)
    const h1 = container.querySelector('h1')
    expect(h1?.textContent).toBe(HEADING_TEXT)
  })
})

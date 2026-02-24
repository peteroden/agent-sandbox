/**
 * Tests for the ObserveDashboard page component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/preact'
import { ObserveDashboard } from '../../../src/pages/observe/ObserveDashboard'

const MOCK_OBSERVE_RETURN = {
  services: ['test-service'],
  traces: [],
  logs: [],
  metricNames: [],
  selectedTrace: null,
  selectedMetricSeries: null,
  filters: { service: null, traceId: null, spanId: null, since: null },
  autoRefresh: true,
  loading: false,
  error: null,
  refresh: vi.fn(),
  selectTrace: vi.fn(),
  selectMetricSeries: vi.fn(),
  clearData: vi.fn(),
  updateFilters: vi.fn(),
  setAutoRefresh: vi.fn(),
}

vi.mock('../../../src/hooks/useObserve', () => ({
  useObserve: () => MOCK_OBSERVE_RETURN,
}))

describe('ObserveDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the dashboard with all panels', () => {
    render(<ObserveDashboard />)

    expect(screen.getByTestId('observe-dashboard')).toBeTruthy()
    expect(screen.getByTestId('metrics-panel')).toBeTruthy()
    expect(screen.getByTestId('traces-panel')).toBeTruthy()
    expect(screen.getByTestId('logs-panel')).toBeTruthy()
  })

  it('renders the page title', () => {
    render(<ObserveDashboard />)
    expect(screen.getByText('Observe')).toBeTruthy()
  })

  it('renders the service filter dropdown', () => {
    render(<ObserveDashboard />)
    const select = screen.getByRole('combobox') as HTMLSelectElement
    expect(select).toBeTruthy()
    expect(select.options.length).toBe(2) // "All Services" + "test-service"
  })

  it('renders auto-refresh toggle', () => {
    render(<ObserveDashboard />)
    expect(screen.getByText('Auto-refresh')).toBeTruthy()
  })

  it('renders refresh and clear buttons', () => {
    render(<ObserveDashboard />)
    expect(screen.getByText('Refresh')).toBeTruthy()
    expect(screen.getByText('Clear Data')).toBeTruthy()
  })

  it('shows error banner when error is present', () => {
    MOCK_OBSERVE_RETURN.error = 'Test error'
    render(<ObserveDashboard />)
    expect(screen.getByTestId('error-banner')).toBeTruthy()
    expect(screen.getByText('Test error')).toBeTruthy()
    MOCK_OBSERVE_RETURN.error = null
  })

  it('shows loading state on refresh button', () => {
    MOCK_OBSERVE_RETURN.loading = true
    render(<ObserveDashboard />)
    expect(screen.getByText('Loading…')).toBeTruthy()
    MOCK_OBSERVE_RETURN.loading = false
  })

  it('shows empty state messages for panels', () => {
    render(<ObserveDashboard />)
    expect(screen.getByText('No traces yet')).toBeTruthy()
    expect(screen.getByText('No logs yet')).toBeTruthy()
  })
})

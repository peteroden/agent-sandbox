/**
 * Tests for the useObserve hook.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/preact'
import { useObserve } from '../../src/hooks/useObserve'

const MOCK_SERVICES = [{ name: 'test-service' }]
const MOCK_TRACES = [{
  trace_id: 'abc123',
  root_span_name: 'GET /test',
  service_name: 'test-service',
  start_time_unix_nano: 1700000000000000000,
  duration_ms: 100,
  span_count: 3,
}]
const MOCK_LOGS = [{
  timestamp_unix_nano: 1700000000000000000,
  trace_id: 'abc123',
  span_id: 'span-1',
  severity_number: 9,
  severity_text: 'INFO',
  body: 'Test log',
  attributes: {},
  resource_attributes: {},
  service_name: 'test-service',
}]
const MOCK_METRICS = [{
  name: 'http.request.duration',
  description: 'Duration',
  unit: 'ms',
  type: 'gauge',
  latest_value: 42,
  service_name: 'test-service',
}]

const mockFetch = vi.fn()

function mockFetchSuccess() {
  mockFetch.mockImplementation((url: string) => {
    if (url.includes('/services')) return Promise.resolve({ ok: true, json: () => Promise.resolve(MOCK_SERVICES) })
    if (url.includes('/traces') && !url.includes('/logs')) return Promise.resolve({ ok: true, json: () => Promise.resolve(MOCK_TRACES) })
    if (url.includes('/logs')) return Promise.resolve({ ok: true, json: () => Promise.resolve(MOCK_LOGS) })
    if (url.includes('/metrics')) return Promise.resolve({ ok: true, json: () => Promise.resolve(MOCK_METRICS) })
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
  })
}

describe('useObserve', () => {
  beforeEach(() => {
    globalThis.fetch = mockFetch
    mockFetchSuccess()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches initial data on mount', async () => {
    const { result } = renderHook(() => useObserve())

    await waitFor(() => {
      expect(result.current.services).toEqual(['test-service'])
    })

    expect(result.current.traces).toEqual(MOCK_TRACES)
    expect(result.current.logs).toEqual(MOCK_LOGS)
    expect(result.current.metricNames).toEqual(MOCK_METRICS)
  })

  it('starts with auto-refresh enabled', () => {
    const { result } = renderHook(() => useObserve())
    expect(result.current.autoRefresh).toBe(true)
  })

  it('can toggle auto-refresh', async () => {
    const { result } = renderHook(() => useObserve())

    act(() => {
      result.current.setAutoRefresh(false)
    })

    expect(result.current.autoRefresh).toBe(false)
  })

  it('updates filters', async () => {
    const { result } = renderHook(() => useObserve())

    act(() => {
      result.current.updateFilters({ service: 'test-service' })
    })

    expect(result.current.filters.service).toBe('test-service')
  })

  it('handles fetch errors', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useObserve())

    await waitFor(() => {
      expect(result.current.error).toBe('Network error')
    })
  })

  it('handles non-ok responses', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500, statusText: 'Internal Server Error' })

    const { result } = renderHook(() => useObserve())

    await waitFor(() => {
      expect(result.current.error).toBe('HTTP 500: Internal Server Error')
    })
  })
})

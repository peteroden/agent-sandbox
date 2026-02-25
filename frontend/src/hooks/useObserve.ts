/**
 * Custom hook for fetching and managing observe dashboard data.
 *
 * Provides typed data for traces, logs, metrics, and services with
 * auto-refresh polling and filter state management.
 */

import { useState, useEffect, useCallback, useRef } from 'preact/hooks'

export interface SpanRecord {
  trace_id: string
  span_id: string
  parent_span_id: string
  name: string
  service_name: string
  kind: number
  status: number
  start_time_unix_nano: number
  end_time_unix_nano: number
  duration_ms: number
  attributes: Record<string, unknown>
  events: Array<{
    name: string
    timestamp_unix_nano: number
    attributes: Record<string, unknown>
  }>
}

export interface TraceSummary {
  trace_id: string
  root_span_name: string
  service_name: string
  start_time_unix_nano: number
  duration_ms: number
  span_count: number
}

export interface TraceDetail {
  trace_id: string
  spans: SpanRecord[]
}

export interface LogRecord {
  timestamp_unix_nano: number
  trace_id: string
  span_id: string
  severity_number: number
  severity_text: string
  body: string
  attributes: Record<string, unknown>
  resource_attributes: Record<string, unknown>
  service_name: string
}

export interface MetricName {
  name: string
  description: string
  unit: string
  type: string
  latest_value: number
  service_name: string
}

export interface MetricSeriesPoint {
  timestamp_unix_nano: number
  value: number
}

export interface MetricSeries {
  name: string
  description: string
  unit: string
  points: MetricSeriesPoint[]
}

export interface ObserveFilters {
  service: string | null
  traceId: string | null
  spanId: string | null
  since: number | null
}

export interface ObserveState {
  services: string[]
  traces: TraceSummary[]
  logs: LogRecord[]
  metricNames: MetricName[]
  selectedTrace: TraceDetail | null
  selectedMetricSeries: MetricSeries | null
  filters: ObserveFilters
  autoRefresh: boolean
  loading: boolean
  error: string | null
}

const DEFAULT_POLL_INTERVAL_MS = 5000
const BASE_URL = '/api/observe'

// Resolve the native (un-instrumented) fetch lazily to bypass OTel zone.js
// patching in the browser, while still allowing tests to mock global.fetch.
function getNativeFetch(): typeof fetch {
  return (globalThis as Record<string, unknown>).__zone_symbol__fetch as typeof fetch ?? fetch
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await getNativeFetch()(url)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  return response.json()
}

function buildParams(filters: ObserveFilters): URLSearchParams {
  const params = new URLSearchParams()
  if (filters.service) params.set('service', filters.service)
  if (filters.traceId) params.set('trace_id', filters.traceId)
  if (filters.spanId) params.set('span_id', filters.spanId)
  if (filters.since) params.set('since', String(filters.since))
  return params
}

export function useObserve() {
  const [services, setServices] = useState<string[]>([])
  const [traces, setTraces] = useState<TraceSummary[]>([])
  const [logs, setLogs] = useState<LogRecord[]>([])
  const [metricNames, setMetricNames] = useState<MetricName[]>([])
  const [selectedTrace, setSelectedTrace] = useState<TraceDetail | null>(null)
  const [selectedMetricSeries, setSelectedMetricSeries] = useState<MetricSeries | null>(null)
  const [filters, setFilters] = useState<ObserveFilters>({
    service: null,
    traceId: null,
    spanId: null,
    since: null,
  })
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = buildParams(filters)
      const qs = params.toString()
      const suffix = qs ? `?${qs}` : ''

      const [svcData, traceData, logData, metricData] = await Promise.all([
        fetchJson<Array<{ name: string }>>(`${BASE_URL}/services`),
        fetchJson<TraceSummary[]>(`${BASE_URL}/traces${suffix}`),
        fetchJson<LogRecord[]>(`${BASE_URL}/logs${suffix}`),
        fetchJson<MetricName[]>(`${BASE_URL}/metrics${filters.service ? `?service=${filters.service}` : ''}`),
      ])

      setServices(svcData.map((s) => s.name))
      setTraces(traceData)
      setLogs(logData)
      setMetricNames(metricData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [filters])

  const selectTrace = useCallback(async (traceId: string) => {
    try {
      const detail = await fetchJson<TraceDetail>(`${BASE_URL}/traces/${traceId}`)
      setSelectedTrace(detail)
      setFilters((prev) => ({ ...prev, traceId }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }, [])

  const selectMetricSeries = useCallback(async (name: string) => {
    try {
      const params = new URLSearchParams()
      if (filters.service) params.set('service', filters.service)
      if (filters.since) params.set('since', String(filters.since))
      const qs = params.toString()
      const suffix = qs ? `?${qs}` : ''
      const series = await fetchJson<MetricSeries>(`${BASE_URL}/metrics/${encodeURIComponent(name)}/series${suffix}`)
      setSelectedMetricSeries(series)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }, [filters.service, filters.since])

  const clearData = useCallback(async () => {
    try {
      const response = await getNativeFetch()(`${BASE_URL}/data`, { method: 'DELETE' })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      await refresh()
      setSelectedTrace(null)
      setSelectedMetricSeries(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear data')
    }
  }, [refresh])

  const updateFilters = useCallback((updates: Partial<ObserveFilters>) => {
    setFilters((prev) => ({ ...prev, ...updates }))
    if ('traceId' in updates && updates.traceId === null) {
      setSelectedTrace(null)
    }
  }, [])

  // Auto-refresh polling
  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    if (autoRefresh) {
      intervalRef.current = setInterval(refresh, DEFAULT_POLL_INTERVAL_MS)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [autoRefresh, refresh])

  // Initial fetch
  useEffect(() => {
    refresh()
  }, [refresh])

  return {
    services,
    traces,
    logs,
    metricNames,
    selectedTrace,
    selectedMetricSeries,
    filters,
    autoRefresh,
    loading,
    error,
    refresh,
    selectTrace,
    selectMetricSeries,
    clearData,
    updateFilters,
    setAutoRefresh,
  }
}

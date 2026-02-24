/**
 * Main observe dashboard layout with three panels:
 * metrics (top), traces (middle), logs (bottom).
 */

import { useObserve } from '../../hooks/useObserve'
import { TraceList } from './TraceList'
import { TraceDetail } from './TraceDetail'
import { LogList } from './LogList'
import { MetricsPanel } from './MetricsPanel'
import { SpanDetail } from './SpanDetail'
import type { SpanRecord } from '../../hooks/useObserve'
import { useState } from 'preact/hooks'

export function ObserveDashboard() {
  const observe = useObserve()
  const [selectedSpan, setSelectedSpan] = useState<SpanRecord | null>(null)

  const activeFilters: Array<{ label: string; onClear: () => void }> = []
  if (observe.filters.service) {
    activeFilters.push({
      label: `Service: ${observe.filters.service}`,
      onClear: () => observe.updateFilters({ service: null }),
    })
  }
  if (observe.filters.traceId) {
    activeFilters.push({
      label: `Trace: ${observe.filters.traceId.slice(0, 16)}…`,
      onClear: () => {
        observe.updateFilters({ traceId: null, spanId: null })
        setSelectedSpan(null)
      },
    })
  }
  if (observe.filters.spanId) {
    activeFilters.push({
      label: `Span: ${observe.filters.spanId.slice(0, 16)}…`,
      onClear: () => {
        observe.updateFilters({ spanId: null })
        setSelectedSpan(null)
      },
    })
  }

  return (
    <div class="container mx-auto px-4" data-testid="observe-dashboard">
      <div class="flex items-center justify-between mb-4">
        <h1 class="text-2xl font-bold text-gray-900">Observe</h1>
        <div class="flex items-center gap-3">
          <select
            class="border rounded px-2 py-1 text-sm"
            value={observe.filters.service ?? ''}
            onChange={(e) => {
              const value = (e.target as HTMLSelectElement).value
              observe.updateFilters({ service: value || null })
            }}
          >
            <option value="">All Services</option>
            {observe.services.map((svc) => (
              <option key={svc} value={svc}>{svc}</option>
            ))}
          </select>
          <label class="flex items-center gap-1 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={observe.autoRefresh}
              onChange={(e) => observe.setAutoRefresh((e.target as HTMLInputElement).checked)}
            />
            Auto-refresh
          </label>
          <button
            class="text-sm text-red-600 hover:text-red-800"
            onClick={observe.clearData}
          >
            Clear Data
          </button>
          <button
            class="text-sm text-blue-600 hover:text-blue-800"
            onClick={observe.refresh}
            disabled={observe.loading}
          >
            {observe.loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
      </div>

      {activeFilters.length > 0 && (
        <div class="flex gap-2 mb-3" data-testid="active-filters">
          {activeFilters.map((f) => (
            <span
              key={f.label}
              class="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs"
            >
              {f.label}
              <button
                class="ml-1 text-blue-600 hover:text-blue-900"
                onClick={f.onClear}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {observe.error && (
        <div class="mb-4 p-3 bg-red-50 text-red-700 rounded text-sm" data-testid="error-banner">
          {observe.error}
        </div>
      )}

      <div class="flex gap-4">
        <div class="flex-1 space-y-4">
          {/* Metrics panel */}
          <div data-testid="metrics-panel">
            <MetricsPanel
              metricNames={observe.metricNames}
              selectedSeries={observe.selectedMetricSeries}
              onSelectMetric={observe.selectMetricSeries}
              selectedTraceTimeRange={
                observe.selectedTrace?.spans.length
                  ? {
                    start: Math.min(...observe.selectedTrace.spans.map((s) => s.start_time_unix_nano)),
                    end: Math.max(...observe.selectedTrace.spans.map((s) => s.end_time_unix_nano)),
                  }
                  : null
              }
            />
          </div>

          {/* Traces panel */}
          <div data-testid="traces-panel">
            {observe.selectedTrace ? (
              <TraceDetail
                trace={observe.selectedTrace}
                onSelectSpan={(span) => {
                  setSelectedSpan(span)
                  observe.updateFilters({ spanId: span.span_id })
                }}
                selectedSpanId={selectedSpan?.span_id ?? null}
              />
            ) : (
              <TraceList
                traces={observe.traces}
                onSelectTrace={observe.selectTrace}
                selectedTraceId={observe.filters.traceId}
              />
            )}
          </div>

          {/* Logs panel */}
          <div data-testid="logs-panel">
            <LogList
              logs={observe.logs}
              onClickTraceId={(traceId) => observe.selectTrace(traceId)}
            />
          </div>
        </div>

        {/* Span detail side panel */}
        {selectedSpan && (
          <div class="w-80 shrink-0">
            <SpanDetail
              span={selectedSpan}
              onClose={() => {
                setSelectedSpan(null)
                observe.updateFilters({ spanId: null })
              }}
              onViewLogs={() => observe.updateFilters({ spanId: selectedSpan.span_id })}
            />
          </div>
        )}
      </div>
    </div>
  )
}

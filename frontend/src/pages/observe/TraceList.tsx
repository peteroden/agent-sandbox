/**
 * Table of recent traces with summary info.
 * Row click selects a trace for detail view.
 */

import type { TraceSummary } from '../../hooks/useObserve'

interface TraceListProps {
  traces: TraceSummary[]
  onSelectTrace: (traceId: string) => void
  selectedTraceId: string | null
}

function formatDuration(ms: number): string {
  if (ms < 1) return `${(ms * 1000).toFixed(0)}µs`
  if (ms < 1000) return `${ms.toFixed(1)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

function formatTimestamp(nanos: number): string {
  return new Date(nanos / 1_000_000).toLocaleTimeString()
}

export function TraceList({ traces, onSelectTrace, selectedTraceId }: TraceListProps) {
  if (traces.length === 0) {
    return (
      <div class="bg-white rounded-lg shadow p-4">
        <h2 class="text-lg font-semibold mb-2">Traces</h2>
        <p class="text-gray-500 text-sm">No traces yet</p>
      </div>
    )
  }

  return (
    <div class="bg-white rounded-lg shadow">
      <h2 class="text-lg font-semibold px-4 pt-4 pb-2">Traces</h2>
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-gray-500 border-b">
            <th class="px-4 py-2">Time</th>
            <th class="px-4 py-2">Root Span</th>
            <th class="px-4 py-2">Service</th>
            <th class="px-4 py-2 text-right">Duration</th>
            <th class="px-4 py-2 text-right">Spans</th>
          </tr>
        </thead>
        <tbody>
          {traces.map((trace) => (
            <tr
              key={trace.trace_id}
              class={`cursor-pointer hover:bg-blue-50 border-b ${
                selectedTraceId === trace.trace_id ? 'bg-blue-100' : ''
              }`}
              onClick={() => onSelectTrace(trace.trace_id)}
            >
              <td class="px-4 py-2 text-gray-600">{formatTimestamp(trace.start_time_unix_nano)}</td>
              <td class="px-4 py-2 font-mono text-xs">{trace.root_span_name || '—'}</td>
              <td class="px-4 py-2">{trace.service_name || '—'}</td>
              <td class="px-4 py-2 text-right font-mono">{formatDuration(trace.duration_ms)}</td>
              <td class="px-4 py-2 text-right">{trace.span_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

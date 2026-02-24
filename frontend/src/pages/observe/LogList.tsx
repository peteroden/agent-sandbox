/**
 * Structured log table with severity badges and trace correlation links.
 */

import type { LogRecord } from '../../hooks/useObserve'

interface LogListProps {
  logs: LogRecord[]
  onClickTraceId: (traceId: string) => void
}

const SEVERITY_COLORS: Record<string, string> = {
  TRACE: 'bg-gray-100 text-gray-600',
  DEBUG: 'bg-gray-200 text-gray-700',
  INFO: 'bg-blue-100 text-blue-700',
  WARN: 'bg-yellow-100 text-yellow-800',
  ERROR: 'bg-red-100 text-red-700',
  FATAL: 'bg-red-200 text-red-900',
}

function formatTimestamp(nanos: number): string {
  return new Date(nanos / 1_000_000).toLocaleTimeString()
}

function severityClass(text: string): string {
  return SEVERITY_COLORS[text.toUpperCase()] ?? 'bg-gray-100 text-gray-600'
}

export function LogList({ logs, onClickTraceId }: LogListProps) {
  if (logs.length === 0) {
    return (
      <div class="bg-white rounded-lg shadow p-4">
        <h2 class="text-lg font-semibold mb-2">Logs</h2>
        <p class="text-gray-500 text-sm">No logs yet</p>
      </div>
    )
  }

  return (
    <div class="bg-white rounded-lg shadow">
      <h2 class="text-lg font-semibold px-4 pt-4 pb-2">Logs</h2>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-gray-500 border-b">
              <th class="px-4 py-2">Time</th>
              <th class="px-4 py-2">Severity</th>
              <th class="px-4 py-2">Body</th>
              <th class="px-4 py-2">Service</th>
              <th class="px-4 py-2">Trace</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log, idx) => (
              <tr key={idx} class="border-b hover:bg-gray-50">
                <td class="px-4 py-2 text-gray-600 whitespace-nowrap">
                  {formatTimestamp(log.timestamp_unix_nano)}
                </td>
                <td class="px-4 py-2">
                  <span class={`px-2 py-0.5 rounded text-xs font-medium ${severityClass(log.severity_text)}`}>
                    {log.severity_text || 'UNKNOWN'}
                  </span>
                </td>
                <td class="px-4 py-2 font-mono text-xs max-w-md truncate">
                  {log.body}
                </td>
                <td class="px-4 py-2 text-gray-600">{log.service_name || '—'}</td>
                <td class="px-4 py-2">
                  {log.trace_id ? (
                    <button
                      class="text-blue-600 hover:text-blue-800 font-mono text-xs"
                      onClick={() => onClickTraceId(log.trace_id)}
                    >
                      {log.trace_id.slice(0, 8)}…
                    </button>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

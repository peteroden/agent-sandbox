/**
 * Metrics panel with metric selector and time-series chart using recharts.
 */

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceArea, ResponsiveContainer } from 'recharts'
import type { MetricName, MetricSeries } from '../../hooks/useObserve'

interface MetricsPanelProps {
  metricNames: MetricName[]
  selectedSeries: MetricSeries | null
  onSelectMetric: (name: string) => void
  selectedTraceTimeRange: { start: number; end: number } | null
}

function formatTimestamp(nanos: number): string {
  return new Date(nanos / 1_000_000).toLocaleTimeString()
}

export function MetricsPanel({
  metricNames,
  selectedSeries,
  onSelectMetric,
  selectedTraceTimeRange,
}: MetricsPanelProps) {
  if (metricNames.length === 0) {
    return (
      <div class="bg-white rounded-lg shadow p-4">
        <h2 class="text-lg font-semibold mb-2">Metrics</h2>
        <p class="text-gray-500 text-sm">No metrics yet</p>
      </div>
    )
  }

  const chartData = selectedSeries?.points.map((p) => ({
    time: p.timestamp_unix_nano,
    value: p.value,
    label: formatTimestamp(p.timestamp_unix_nano),
  })) ?? []

  return (
    <div class="bg-white rounded-lg shadow p-4">
      <div class="flex items-center gap-3 mb-3">
        <h2 class="text-lg font-semibold">Metrics</h2>
        <select
          class="border rounded px-2 py-1 text-sm"
          value={selectedSeries?.name ?? ''}
          onChange={(e) => {
            const name = (e.target as HTMLSelectElement).value
            if (name) onSelectMetric(name)
          }}
        >
          <option value="">Select a metric…</option>
          {metricNames.map((m) => (
            <option key={m.name} value={m.name}>
              {m.name} ({m.latest_value} {m.unit})
            </option>
          ))}
        </select>
      </div>

      {selectedSeries && chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#3b82f6"
              dot={false}
              strokeWidth={2}
            />
            {selectedTraceTimeRange && (
              <ReferenceArea
                x1={formatTimestamp(selectedTraceTimeRange.start)}
                x2={formatTimestamp(selectedTraceTimeRange.end)}
                fill="#3b82f6"
                fillOpacity={0.1}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      ) : selectedSeries ? (
        <p class="text-gray-500 text-sm">No data points for this metric</p>
      ) : null}

      {!selectedSeries && (
        <div class="grid grid-cols-2 gap-2 mt-2">
          {metricNames.map((m) => (
            <button
              key={m.name}
              class="text-left p-2 border rounded hover:bg-blue-50 text-sm"
              onClick={() => onSelectMetric(m.name)}
            >
              <div class="font-medium truncate">{m.name}</div>
              <div class="text-gray-500 text-xs">
                {m.latest_value} {m.unit} · {m.service_name}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

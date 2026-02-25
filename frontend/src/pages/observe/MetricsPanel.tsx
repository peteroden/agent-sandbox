/**
 * Metrics panel with metric selector and SVG time-series line chart.
 */

import type { MetricName, MetricSeries } from '../../hooks/useObserve'

interface MetricsPanelProps {
  metricNames: MetricName[]
  selectedSeries: MetricSeries | null
  onSelectMetric: (name: string) => void
  selectedTraceTimeRange: { start: number; end: number } | null
}

const CHART_W = 600
const CHART_H = 180
const PAD = { top: 10, right: 10, bottom: 30, left: 50 }
const PLOT_W = CHART_W - PAD.left - PAD.right
const PLOT_H = CHART_H - PAD.top - PAD.bottom

function formatTime(nanos: number): string {
  return new Date(nanos / 1_000_000).toLocaleTimeString()
}

function formatValue(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}k`
  return v % 1 === 0 ? String(v) : v.toFixed(1)
}

interface SvgLineChartProps {
  points: { timestamp_unix_nano: number; value: number }[]
  highlightRange: { start: number; end: number } | null
}

function SvgLineChart({ points, highlightRange }: SvgLineChartProps) {
  if (points.length === 0) return null

  const times = points.map((p) => p.timestamp_unix_nano)
  const vals = points.map((p) => p.value)
  const minT = Math.min(...times)
  const maxT = Math.max(...times)
  const minV = Math.min(...vals)
  const maxV = Math.max(...vals)
  const rangeT = maxT - minT || 1
  const rangeV = maxV - minV || 1
  const padV = rangeV * 0.1

  const scaleX = (t: number) => PAD.left + ((t - minT) / rangeT) * PLOT_W
  const scaleY = (v: number) =>
    PAD.top + PLOT_H - ((v - (minV - padV)) / (rangeV + 2 * padV)) * PLOT_H

  const pathD = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${scaleX(p.timestamp_unix_nano).toFixed(1)},${scaleY(p.value).toFixed(1)}`)
    .join(' ')

  const yTicks = 5
  const yLabels = Array.from({ length: yTicks }, (_, i) => {
    const v = minV - padV + ((rangeV + 2 * padV) * (yTicks - 1 - i)) / (yTicks - 1)
    return { y: scaleY(v), label: formatValue(v) }
  })

  const xTicks = Math.min(points.length, 5)
  const xLabels = Array.from({ length: xTicks }, (_, i) => {
    const idx = Math.round((i * (points.length - 1)) / (xTicks - 1))
    const p = points[idx]
    return { x: scaleX(p.timestamp_unix_nano), label: formatTime(p.timestamp_unix_nano) }
  })

  return (
    <svg width={CHART_W} height={CHART_H} class="overflow-visible">
      {/* Grid lines */}
      {yLabels.map((tick) => (
        <line
          key={tick.label}
          x1={PAD.left}
          y1={tick.y}
          x2={PAD.left + PLOT_W}
          y2={tick.y}
          stroke="#e5e7eb"
          stroke-dasharray="3 3"
        />
      ))}

      {/* Highlight range */}
      {highlightRange && (
        <rect
          x={scaleX(highlightRange.start)}
          y={PAD.top}
          width={Math.max(1, scaleX(highlightRange.end) - scaleX(highlightRange.start))}
          height={PLOT_H}
          fill="#3b82f6"
          fill-opacity="0.1"
        />
      )}

      {/* Data line */}
      <path d={pathD} fill="none" stroke="#3b82f6" stroke-width="2" />

      {/* Y axis labels */}
      {yLabels.map((tick) => (
        <text
          key={tick.label}
          x={PAD.left - 6}
          y={tick.y + 3}
          text-anchor="end"
          font-size="10"
          fill="#6b7280"
        >
          {tick.label}
        </text>
      ))}

      {/* X axis labels */}
      {xLabels.map((tick) => (
        <text
          key={tick.label}
          x={tick.x}
          y={PAD.top + PLOT_H + 16}
          text-anchor="middle"
          font-size="10"
          fill="#6b7280"
        >
          {tick.label}
        </text>
      ))}

      {/* Axes */}
      <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={PAD.top + PLOT_H} stroke="#d1d5db" />
      <line x1={PAD.left} y1={PAD.top + PLOT_H} x2={PAD.left + PLOT_W} y2={PAD.top + PLOT_H} stroke="#d1d5db" />
    </svg>
  )
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

      {selectedSeries && selectedSeries.points.length > 0 ? (
        <div style={{ overflowX: 'auto' }}>
          <SvgLineChart points={selectedSeries.points} highlightRange={selectedTraceTimeRange} />
          <p class="text-gray-400 text-xs mt-1">
            {selectedSeries.points.length} points · {selectedSeries.unit || 'units'}
          </p>
        </div>
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

/**
 * Waterfall/gantt view of spans in a trace.
 * Uses custom positioned elements for the timeline visualization.
 */

import type { TraceDetail as TraceDetailType, SpanRecord } from '../../hooks/useObserve'

interface TraceDetailProps {
  trace: TraceDetailType
  onSelectSpan: (span: SpanRecord) => void
  selectedSpanId: string | null
}

function formatDuration(ms: number): string {
  if (ms < 1) return `${(ms * 1000).toFixed(0)}µs`
  if (ms < 1000) return `${ms.toFixed(1)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

interface SpanTree {
  span: SpanRecord
  children: SpanTree[]
  depth: number
}

function buildSpanTree(spans: SpanRecord[]): SpanTree[] {
  const byId = new Map<string, SpanTree>()
  const roots: SpanTree[] = []

  for (const span of spans) {
    byId.set(span.span_id, { span, children: [], depth: 0 })
  }

  for (const node of byId.values()) {
    const parentId = node.span.parent_span_id
    if (parentId && byId.has(parentId)) {
      const parent = byId.get(parentId)!
      node.depth = parent.depth + 1
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  }

  return roots
}

function flattenTree(nodes: SpanTree[]): SpanTree[] {
  const result: SpanTree[] = []
  for (const node of nodes) {
    result.push(node)
    result.push(...flattenTree(node.children))
  }
  return result
}

export function TraceDetail({ trace, onSelectSpan, selectedSpanId }: TraceDetailProps) {
  if (trace.spans.length === 0) {
    return (
      <div class="bg-white rounded-lg shadow p-4">
        <h2 class="text-lg font-semibold mb-2">Trace Detail</h2>
        <p class="text-gray-500 text-sm">No spans found</p>
      </div>
    )
  }

  const tree = buildSpanTree(trace.spans)
  const flatSpans = flattenTree(tree)

  const traceStart = Math.min(...trace.spans.map((s) => s.start_time_unix_nano))
  const traceEnd = Math.max(...trace.spans.map((s) => s.end_time_unix_nano))
  const traceDuration = traceEnd - traceStart

  return (
    <div class="bg-white rounded-lg shadow">
      <div class="px-4 pt-4 pb-2 flex items-center justify-between">
        <h2 class="text-lg font-semibold">
          Trace: <span class="font-mono text-sm">{trace.trace_id.slice(0, 16)}…</span>
        </h2>
        <span class="text-sm text-gray-500">
          {trace.spans.length} spans · {formatDuration(traceDuration / 1_000_000)}
        </span>
      </div>
      <div class="px-4 pb-4">
        {flatSpans.map(({ span, depth }) => {
          const offsetPct = traceDuration > 0
            ? ((span.start_time_unix_nano - traceStart) / traceDuration) * 100
            : 0
          const widthPct = traceDuration > 0
            ? ((span.end_time_unix_nano - span.start_time_unix_nano) / traceDuration) * 100
            : 100

          return (
            <div
              key={span.span_id}
              class={`flex items-center gap-2 py-1 cursor-pointer hover:bg-blue-50 rounded ${
                selectedSpanId === span.span_id ? 'bg-blue-100' : ''
              }`}
              onClick={() => onSelectSpan(span)}
            >
              <div
                class="text-xs truncate text-gray-700 shrink-0"
                style={{ width: '200px', paddingLeft: `${depth * 16}px` }}
              >
                {span.name}
              </div>
              <div class="text-xs text-gray-500 shrink-0 w-20 truncate">
                {span.service_name}
              </div>
              <div class="flex-1 relative h-5 bg-gray-100 rounded">
                <div
                  class="absolute h-full bg-blue-400 rounded"
                  style={{
                    left: `${offsetPct}%`,
                    width: `${Math.max(widthPct, 0.5)}%`,
                  }}
                />
              </div>
              <div class="text-xs text-gray-600 shrink-0 w-16 text-right font-mono">
                {formatDuration(span.duration_ms)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/**
 * Waterfall/gantt view of spans in a trace with collapsible tree nesting.
 * Parent spans can be expanded/collapsed to show/hide children.
 */

import { useState, useMemo, useCallback } from 'preact/hooks'
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

export interface SpanTree {
  span: SpanRecord
  children: SpanTree[]
  depth: number
}

export function buildSpanTree(spans: SpanRecord[]): SpanTree[] {
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

  // Sort children by start time within each parent
  function sortChildren(nodes: SpanTree[]) {
    nodes.sort((a, b) => a.span.start_time_unix_nano - b.span.start_time_unix_nano)
    for (const node of nodes) sortChildren(node.children)
  }
  sortChildren(roots)

  return roots
}

export function flattenTree(
  nodes: SpanTree[],
  collapsed: Set<string>,
): SpanTree[] {
  const result: SpanTree[] = []
  for (const node of nodes) {
    result.push(node)
    if (!collapsed.has(node.span.span_id)) {
      result.push(...flattenTree(node.children, collapsed))
    }
  }
  return result
}

function descendantCount(node: SpanTree): number {
  let count = node.children.length
  for (const child of node.children) count += descendantCount(child)
  return count
}

const DEPTH_BAR_COLORS = [
  'bg-blue-500',
  'bg-indigo-400',
  'bg-violet-400',
  'bg-purple-400',
  'bg-fuchsia-400',
]

function barColorForSpan(status: number, depth: number): string {
  if (status === 2) return 'bg-red-500'
  if (status === 1) return 'bg-green-500'
  return DEPTH_BAR_COLORS[depth % DEPTH_BAR_COLORS.length]
}

export function TraceDetail({ trace, onSelectSpan, selectedSpanId }: TraceDetailProps) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())

  const tree = useMemo(() => buildSpanTree(trace.spans), [trace.spans])

  const traceStart = useMemo(
    () => Math.min(...trace.spans.map((s) => s.start_time_unix_nano)),
    [trace.spans],
  )
  const traceEnd = useMemo(
    () => Math.max(...trace.spans.map((s) => s.end_time_unix_nano)),
    [trace.spans],
  )
  const traceDuration = traceEnd - traceStart

  const flatSpans = useMemo(
    () => flattenTree(tree, collapsed),
    [tree, collapsed],
  )

  const toggleCollapse = useCallback((spanId: string, e: MouseEvent) => {
    e.stopPropagation()
    setCollapsed((prev) => {
      const next = new Set(prev)
      if (next.has(spanId)) next.delete(spanId)
      else next.add(spanId)
      return next
    })
  }, [])

  const collapseAll = useCallback(() => {
    const parents = new Set<string>()
    function collect(nodes: SpanTree[]) {
      for (const n of nodes) {
        if (n.children.length > 0) parents.add(n.span.span_id)
        collect(n.children)
      }
    }
    collect(tree)
    setCollapsed(parents)
  }, [tree])

  const expandAll = useCallback(() => setCollapsed(new Set()), [])

  if (trace.spans.length === 0) {
    return (
      <div class="bg-white rounded-lg shadow p-4">
        <h2 class="text-lg font-semibold mb-2">Trace Detail</h2>
        <p class="text-gray-500 text-sm">No spans found</p>
      </div>
    )
  }

  const hiddenCount = trace.spans.length - flatSpans.length

  return (
    <div class="bg-white rounded-lg shadow">
      <div class="px-4 pt-4 pb-2 flex items-center justify-between">
        <h2 class="text-lg font-semibold">
          Trace: <span class="font-mono text-sm">{trace.trace_id.slice(0, 16)}…</span>
        </h2>
        <div class="flex items-center gap-3">
          <span class="text-sm text-gray-500">
            {trace.spans.length} spans · {formatDuration(traceDuration / 1_000_000)}
            {hiddenCount > 0 && ` · ${hiddenCount} hidden`}
          </span>
          <button
            class="text-xs text-blue-600 hover:text-blue-800"
            onClick={expandAll}
          >
            Expand all
          </button>
          <button
            class="text-xs text-blue-600 hover:text-blue-800"
            onClick={collapseAll}
          >
            Collapse all
          </button>
        </div>
      </div>
      <div class="pb-4 overflow-x-auto">
        {flatSpans.map(({ span, depth, children }) => {
          // Position bar using absolute timestamps on the trace timeline
          const leftPct = traceDuration > 0
            ? ((span.start_time_unix_nano - traceStart) / traceDuration) * 100
            : 0
          const widthPct = traceDuration > 0
            ? ((span.end_time_unix_nano - span.start_time_unix_nano) / traceDuration) * 100
            : 100

          const hasChildren = children.length > 0
          const isCollapsed = collapsed.has(span.span_id)
          const barColor = barColorForSpan(span.status, depth)
          const hiddenDescendants = isCollapsed ? descendantCount({ span, children, depth }) : 0

          return (
            <div
              key={span.span_id}
              class={`flex items-center gap-2 py-0.5 cursor-pointer hover:bg-blue-50 ${
                selectedSpanId === span.span_id ? 'bg-blue-100' : ''
              }`}
              onClick={() => onSelectSpan(span)}
            >
              {/* Span name with tree nesting */}
              <div
                class="text-xs truncate text-gray-700 shrink-0 flex items-center"
                style={{ width: '240px', paddingLeft: `${depth * 16 + 4}px` }}
              >
                {hasChildren ? (
                  <button
                    class="w-4 h-4 flex items-center justify-center text-gray-500 hover:text-gray-800 shrink-0 mr-1"
                    onClick={(e) => toggleCollapse(span.span_id, e)}
                    aria-label={isCollapsed ? 'Expand' : 'Collapse'}
                  >
                    {isCollapsed ? '▶' : '▼'}
                  </button>
                ) : (
                  <span class="w-4 mr-1 shrink-0 inline-flex justify-center text-gray-300">·</span>
                )}
                <span class="truncate" title={span.name}>
                  {span.name}
                </span>
                {isCollapsed && hiddenDescendants > 0 && (
                  <span class="ml-1 text-[10px] text-gray-400 shrink-0">
                    +{hiddenDescendants}
                  </span>
                )}
              </div>

              {/* Service name */}
              <div class="text-xs text-gray-500 shrink-0 w-20 truncate" title={span.service_name}>
                {span.service_name}
              </div>

              {/* Gantt bar — absolute timestamp positioning */}
              <div class="flex-1 relative h-5 bg-gray-50 rounded min-w-[120px]">
                <div
                  class={`absolute h-3 top-1 ${barColor} rounded-sm`}
                  style={{
                    left: `${leftPct}%`,
                    width: `${Math.max(widthPct, 0.3)}%`,
                  }}
                />
              </div>

              {/* Duration */}
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

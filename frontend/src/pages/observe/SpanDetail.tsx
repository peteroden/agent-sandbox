/**
 * Side panel showing span attributes, events, and contextual links.
 */

import type { SpanRecord } from '../../hooks/useObserve'

interface SpanDetailProps {
  span: SpanRecord
  onClose: () => void
  onViewLogs: () => void
}

function formatTimestamp(nanos: number): string {
  return new Date(nanos / 1_000_000).toLocaleTimeString()
}

function formatDuration(ms: number): string {
  if (ms < 1) return `${(ms * 1000).toFixed(0)}µs`
  if (ms < 1000) return `${ms.toFixed(1)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

const SPAN_KIND_NAMES: Record<number, string> = {
  0: 'Unspecified',
  1: 'Internal',
  2: 'Server',
  3: 'Client',
  4: 'Producer',
  5: 'Consumer',
}

const STATUS_NAMES: Record<number, string> = {
  0: 'Unset',
  1: 'OK',
  2: 'Error',
}

export function SpanDetail({ span, onClose, onViewLogs }: SpanDetailProps) {
  const attributes = Object.entries(span.attributes)

  return (
    <div class="bg-white rounded-lg shadow p-4" data-testid="span-detail">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-semibold text-sm">Span Detail</h3>
        <button class="text-gray-400 hover:text-gray-600" onClick={onClose}>✕</button>
      </div>

      <dl class="space-y-2 text-sm">
        <div>
          <dt class="text-gray-500">Name</dt>
          <dd class="font-mono text-xs">{span.name}</dd>
        </div>
        <div>
          <dt class="text-gray-500">Service</dt>
          <dd>{span.service_name || '—'}</dd>
        </div>
        <div>
          <dt class="text-gray-500">Kind</dt>
          <dd>{SPAN_KIND_NAMES[span.kind] ?? span.kind}</dd>
        </div>
        <div>
          <dt class="text-gray-500">Status</dt>
          <dd>{STATUS_NAMES[span.status] ?? span.status}</dd>
        </div>
        <div>
          <dt class="text-gray-500">Duration</dt>
          <dd class="font-mono">{formatDuration(span.duration_ms)}</dd>
        </div>
        <div>
          <dt class="text-gray-500">Span ID</dt>
          <dd class="font-mono text-xs">{span.span_id}</dd>
        </div>
        {span.parent_span_id && (
          <div>
            <dt class="text-gray-500">Parent Span ID</dt>
            <dd class="font-mono text-xs">{span.parent_span_id}</dd>
          </div>
        )}
        <div>
          <dt class="text-gray-500">Start</dt>
          <dd>{formatTimestamp(span.start_time_unix_nano)}</dd>
        </div>
        <div>
          <dt class="text-gray-500">End</dt>
          <dd>{formatTimestamp(span.end_time_unix_nano)}</dd>
        </div>
      </dl>

      {attributes.length > 0 && (
        <div class="mt-4">
          <h4 class="text-sm font-medium text-gray-700 mb-1">Attributes</h4>
          <div class="bg-gray-50 rounded p-2 text-xs font-mono space-y-1">
            {attributes.map(([key, value]) => (
              <div key={key}>
                <span class="text-gray-500">{key}:</span>{' '}
                <span class="text-gray-800">{String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {span.events.length > 0 && (
        <div class="mt-4">
          <h4 class="text-sm font-medium text-gray-700 mb-1">Events ({span.events.length})</h4>
          <div class="space-y-1">
            {span.events.map((event, idx) => (
              <div key={idx} class="bg-gray-50 rounded p-2 text-xs">
                <div class="font-medium">{event.name}</div>
                <div class="text-gray-500">{formatTimestamp(event.timestamp_unix_nano)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div class="mt-4 flex gap-2">
        <button
          class="text-sm text-blue-600 hover:text-blue-800"
          onClick={onViewLogs}
        >
          View Logs for Span
        </button>
      </div>
    </div>
  )
}

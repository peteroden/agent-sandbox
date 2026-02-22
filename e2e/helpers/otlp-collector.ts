/**
 * Minimal in-memory OTLP HTTP collector for E2E trace verification.
 *
 * Accepts OTLP protobuf trace exports on POST /v1/traces and stores raw bodies.
 * Provides a query API to check whether spans with a given traceId were received
 * by searching for the 16-byte traceId in the raw protobuf payload.
 *
 * Endpoints:
 *   POST   /v1/traces          — accept OTLP trace export (protobuf or JSON)
 *   POST   /v1/metrics          — accept and discard (200)
 *   POST   /v1/logs             — accept and discard (200)
 *   GET    /api/traces?traceId= — query for traceId presence
 *   DELETE /api/traces          — clear stored data
 */
import {
  createServer,
  type IncomingMessage,
  type Server,
  type ServerResponse,
} from 'node:http'

export const COLLECTOR_PORT = 4319

interface StoredExport {
  body: Buffer
  timestamp: number
}

let server: Server | null = null
const exports: StoredExport[] = []

function handler(req: IncomingMessage, res: ServerResponse): void {
  // OTLP ingest endpoints
  if (req.method === 'POST' && req.url?.startsWith('/v1/')) {
    const chunks: Buffer[] = []
    req.on('data', (chunk: Buffer) => chunks.push(chunk))
    req.on('end', () => {
      if (req.url === '/v1/traces') {
        exports.push({ body: Buffer.concat(chunks), timestamp: Date.now() })
      }
      // Acknowledge all signals (traces, metrics, logs) with 200
      res.writeHead(200, { 'Content-Type': 'application/x-protobuf' })
      res.end()
    })
    return
  }

  // Query API: check whether a traceId was received
  if (req.method === 'GET' && req.url?.startsWith('/api/traces')) {
    const url = new URL(req.url, `http://localhost:${COLLECTOR_PORT}`)
    const traceIdHex = url.searchParams.get('traceId')

    if (!traceIdHex) {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ requestCount: exports.length }))
      return
    }

    // Search for the 16-byte traceId in the raw protobuf bodies.
    // In protobuf wire format, bytes fields are stored verbatim, so the
    // traceId bytes appear directly in the serialized message.
    const traceIdBytes = Buffer.from(traceIdHex, 'hex')
    const matchCount = exports.filter((e) => e.body.includes(traceIdBytes)).length

    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(
      JSON.stringify({ found: matchCount > 0, matchCount, requestCount: exports.length }),
    )
    return
  }

  // Clear stored data
  if (req.method === 'DELETE' && req.url === '/api/traces') {
    exports.length = 0
    res.writeHead(204)
    res.end()
    return
  }

  res.writeHead(404)
  res.end()
}

export async function startCollector(port = COLLECTOR_PORT): Promise<void> {
  return new Promise((resolve, reject) => {
    server = createServer(handler)
    server.on('error', reject)
    server.listen(port, () => {
      console.log(`[otlp-collector] listening on port ${port}`)
      resolve()
    })
  })
}

export async function stopCollector(): Promise<void> {
  return new Promise((resolve) => {
    if (server) {
      server.close(() => {
        console.log('[otlp-collector] stopped')
        resolve()
      })
      server = null
    } else {
      resolve()
    }
  })
}

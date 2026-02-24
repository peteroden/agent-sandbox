---
description: "Plan for a lightweight OTLP dev collector with integrated Preact dashboard"
maturity: experimental
---

## Lightweight OTLP Dev Collector and Dashboard

Replace the heavyweight SigNoz Docker stack with a single-process Python OTLP
collector backed by SQLite, paired with Preact dashboard pages embedded in the
existing frontend. The collector accepts traces, logs, and metrics on port 4318
(OTLP HTTP standard) and exposes a REST query API. The dashboard lives at
`/observe` in the Vite app. Integrated via a new `--observe` flag in `dev.sh`.

### Architecture

```text
Frontend (browser) ──POST /v1/*──→ Vite proxy ──→ ┌─────────────────────┐
Backend (Python)  ──POST /v1/*──────────────────→ │  Python collector    │
                                                  │  :4318               │
Vite :5173                                        │  OTLP ingest (HTTP)  │
├── /observe/*  (Preact dashboard)                │  REST query API      │
├── /api/observe/* → proxy to :4318               │  SQLite storage      │
└── /v1/*          → proxy to :4318               └─────────────────────┘
```

**Key properties:**

* Single Python process, no Docker, no external services
* HTTP only, port 4318 (no gRPC — backend uses `http/protobuf`, frontend uses
  `http/json`)
* Drop-in replacement for SigNoz collector — zero config changes to frontend or
  backend
* Dashboard is a set of Preact pages under `/observe`, self-contained for easy
  future extraction

### Phase 1 — Python OTLP Collector

Create a `collector/` package at the repo root (sibling to `backend/`,
`frontend/`).

#### Step 1: Project scaffold

* `collector/pyproject.toml` — deps: `fastapi`, `uvicorn`,
  `opentelemetry-proto`, `aiosqlite`. Use `src` layout with
  `[tool.hatch.build.targets.wheel] packages = ["src/dev_collector"]` so
  `uv run` resolves the `dev_collector` module correctly.
* `collector/src/dev_collector/__init__.py`
* Use `uv` for environment management per project conventions

#### Step 2: SQLite storage layer

File: `collector/src/dev_collector/storage.py`

Tables:

| Table | Key columns |
| --- | --- |
| `spans` | trace_id, span_id, parent_span_id, name, service_name, kind, status, start_time_unix_nano, end_time_unix_nano, duration_ms, attributes (JSON), events (JSON) |
| `logs` | timestamp_unix_nano, trace_id, span_id, severity_number, severity_text, body, attributes (JSON), resource_attributes (JSON), service_name |
| `metrics` | timestamp_unix_nano, name, description, unit, type, value, attributes (JSON), resource_attributes (JSON), service_name, exemplar_trace_id, exemplar_span_id |

Behaviour:

* Auto-create tables on startup
* DB file at `collector/.dev-collector.db` (gitignored)
* Auto-prune records older than 1 hour (configurable via
  `COLLECTOR_RETAIN_MINUTES`)

#### Step 3: OTLP ingest module (parallel with step 2)

File: `collector/src/dev_collector/ingest.py`

* Decode `application/x-protobuf` bodies using `opentelemetry.proto` message
  classes (`ExportTraceServiceRequest`, `ExportLogsServiceRequest`,
  `ExportMetricsServiceRequest`)
* Decode `application/json` bodies using `google.protobuf.json_format.Parse`
  (frontend sends JSON)
* Extract resource attributes (`service.name`) and flatten into storage-friendly
  dicts
* Return proper OTLP HTTP responses (200 with empty protobuf body)

#### Step 4: FastAPI server and query API (depends on 2, 3)

File: `collector/src/dev_collector/server.py`

OTLP ingest routes:

* `POST /v1/traces`
* `POST /v1/logs`
* `POST /v1/metrics`

Query API routes (all under `/api/observe/`):

| Endpoint | Purpose | Query params |
| --- | --- | --- |
| `GET /api/observe/services` | List known service names | — |
| `GET /api/observe/traces` | Recent traces grouped by trace_id | `service`, `since`, `limit` |
| `GET /api/observe/traces/{trace_id}` | All spans for a trace (flat list, client builds tree) | — |
| `GET /api/observe/traces/{trace_id}/logs` | Logs with matching trace_id | — |
| `GET /api/observe/logs` | Recent logs | `service`, `severity`, `trace_id`, `span_id`, `since`, `limit` |
| `GET /api/observe/metrics` | Known metric names with latest values | `service` |
| `GET /api/observe/metrics/{name}/series` | Time series for a metric | `service`, `since`, `step` |
| `DELETE /api/observe/data` | Clear all stored data | — |

Additional concerns:

* CORS middleware for direct browser access (fallback)
* Lifespan handler: init DB on startup, schedule periodic cleanup

#### Step 5: Pydantic models (parallel with 2–4)

File: `collector/src/dev_collector/models.py`

Response models: `SpanRecord`, `LogRecord`, `MetricRecord`, `TraceSummary`,
`TraceDetail`, `MetricSeries`

#### Step 6: Collector tests (parallel with 2–5)

All tests follow TDD — red, green, refactor.

| File | Coverage |
| --- | --- |
| `collector/tests/conftest.py` | Fixtures for in-memory SQLite, test client |
| `collector/tests/test_ingest.py` | Protobuf and JSON ingest for all 3 signals |
| `collector/tests/test_storage.py` | SQLite CRUD and cleanup |
| `collector/tests/test_query_api.py` | Query endpoint responses and filtering |
| `collector/tests/test_correlation.py` | Trace↔log correlation via trace_id/span_id |

### Phase 2 — Preact Dashboard

#### Step 7: Vite proxy rule

Add to `frontend/vite.config.ts`:

* `/api/observe` → `http://localhost:4318` (no rewrite — collector serves at
  `/api/observe/*`)
* Place alongside existing proxy rules for `/api`, `/ag-ui`, `/mcp`

#### Step 8: Dashboard pages

Create `frontend/src/pages/observe/` with these components:

| Component | Responsibility |
| --- | --- |
| `ObserveDashboard.tsx` | Main layout with 3-panel view (metrics top, traces middle, logs bottom), time range selector, service filter, auto-refresh toggle (5 s) |
| `TraceList.tsx` | Table of recent traces (root span name, service, duration, span count). Row click opens trace detail. |
| `TraceDetail.tsx` | Waterfall/gantt view of spans using custom positioned elements (not a charting lib). Each row shows name, service, duration bar. Click span to see attributes/events and filter logs. |
| `LogList.tsx` | Structured log table (timestamp, severity badge, body, service, trace_id link). Click trace_id → navigate to trace detail. |
| `MetricsPanel.tsx` | Metric selector dropdown + time-series chart (recharts). Exemplar dots link to traces. |
| `SpanDetail.tsx` | Side panel showing span attributes, events, and "View Logs" / "View Metrics" contextual links. |

#### Step 9: Route and nav link

In `frontend/src/app.tsx`:

* Add `<Link>` in the nav bar: "Observe"
* Add `<Route path="/observe/:rest*" component={ObserveDashboard} />`
* Sub-routing within `ObserveDashboard` for `/observe/traces/:traceId` etc.

#### Step 10: Custom hook

File: `frontend/src/hooks/useObserve.ts`

* Fetches from `/api/observe/*` endpoints
* Manages polling interval (auto-refresh)
* Handles time range and service filter state
* Returns typed data for each panel

#### Step 11: Frontend tests (parallel with 8–10)

| File | Coverage |
| --- | --- |
| `frontend/test/pages/observe/ObserveDashboard.test.tsx` | Page rendering and panel layout |
| `frontend/test/hooks/useObserve.test.ts` | Data fetching, polling, filter state |

### Phase 3 — Integration

#### Step 12: `--observe` flag in `dev.sh`

Add alongside the existing `--signoz` flag (mutually exclusive):

```bash
export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="http://localhost:4318/v1/traces"
export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT="http://localhost:4318/v1/logs"
export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT="http://localhost:4318/v1/metrics"
export ENABLE_INSTRUMENTATION=true
export VITE_OTEL_EXPORTER="otlp"
export VITE_OTEL_ENDPOINT=""
```

Start the collector as a `concurrently` process:

```bash
uv run --project collector uvicorn dev_collector.server:app --port 4318 --reload
```

#### Step 13: Gitignore and docs

* Add `collector/.dev-collector.db` to `.gitignore`
* Update `docs/observability.md` with lightweight collector section

### Correlation UX

All three dashboard panels (metrics, traces, logs) are visible simultaneously.
Selecting an item in one panel updates the other two panels in place, keeping
the full picture on screen at all times. No page navigation is needed for
cross-signal correlation.

**Cross-panel interactions:**

* **Click a trace row** → The logs panel filters to that trace's trace_id and
  time window. The metrics panel highlights the time range of the trace and
  filters to the trace's service.
* **Click a span in the waterfall** → The logs panel filters to that span's
  span_id. The metrics panel narrows to the span's time range. The span detail
  side panel opens with attributes, events, and contextual links.
* **Click a trace_id in a log row** → The traces panel selects and scrolls to
  that trace. The waterfall opens. The metrics panel highlights the trace's time
  range.
* **Click an exemplar dot on the metrics chart** → The traces panel selects the
  associated trace and opens its waterfall. The logs panel filters to that
  trace's trace_id.
* **Change the service filter** → All three panels update to show only data from
  the selected service.
* **Change the time range** → All three panels update to the new window.

**Visual feedback:**

* The selected trace row and log rows are highlighted with a distinct background
  colour.
* The metrics chart shows a shaded region corresponding to the selected trace or
  span's time range.
* Active filters (service, trace_id, span_id, time range) are shown as
  dismissible chips above the panels so the user always knows what is filtered.

### Files Modified

| File | Change |
| --- | --- |
| `scripts/dev.sh` | Add `--observe` flag (reference `--signoz` pattern) |
| `frontend/vite.config.ts` | Add `/api/observe` proxy rule |
| `frontend/src/app.tsx` | Add `<Link>` and `<Route>` for `/observe` |
| `docs/observability.md` | Add lightweight collector section |
| `.gitignore` | Add `collector/.dev-collector.db` |

### Files Not Modified

| File | Reason |
| --- | --- |
| `e2e/helpers/otlp-collector.ts` | Stays as E2E test helper on port 4319 |
| SigNoz integration (`--signoz`) | Not modified; will be removed later if observer replaces it |
| `backend/src/agent_sandbox/server.py` | No changes needed (reads OTLP env vars) |
| `scripts/dev.sh` `--signoz` flag | No changes; will be removed in a future cleanup if observer proves stable |
| `frontend/packages/otel-web-sdk/` | No changes needed (browser OTel SDK, sends to whichever collector is running) |

### New Files

**Collector (Python):**

* `collector/pyproject.toml`
* `collector/src/dev_collector/__init__.py`
* `collector/src/dev_collector/server.py`
* `collector/src/dev_collector/storage.py`
* `collector/src/dev_collector/ingest.py`
* `collector/src/dev_collector/models.py`
* `collector/tests/conftest.py`
* `collector/tests/test_ingest.py`
* `collector/tests/test_storage.py`
* `collector/tests/test_query_api.py`
* `collector/tests/test_correlation.py`

**Frontend (Preact):**

* `frontend/src/pages/observe/ObserveDashboard.tsx`
* `frontend/src/pages/observe/TraceList.tsx`
* `frontend/src/pages/observe/TraceDetail.tsx`
* `frontend/src/pages/observe/LogList.tsx`
* `frontend/src/pages/observe/MetricsPanel.tsx`
* `frontend/src/pages/observe/SpanDetail.tsx`
* `frontend/src/hooks/useObserve.ts`
* `frontend/test/pages/observe/ObserveDashboard.test.tsx`
* `frontend/test/hooks/useObserve.test.ts`

### Dependencies

**Collector (Python — 4 direct deps):**

| Package | Purpose |
| --- | --- |
| `fastapi` | HTTP server for OTLP ingest and query API |
| `uvicorn` | ASGI server |
| `opentelemetry-proto` | Protobuf message classes for decoding OTLP payloads |
| `aiosqlite` | Async SQLite access |

**Frontend (npm — 1 new dep):**

| Package | Purpose |
| --- | --- |
| `recharts` | Declarative React charting library for metrics time-series panel |

### Verification

1. `cd collector && uv run pytest` — all collector tests pass
2. `cd frontend && pnpm test --run` — observe page and hook tests pass
3. `./scripts/dev.sh --mock --observe` → open `http://localhost:5173/observe` →
   send a chat message → traces, logs, and metrics appear with full correlation
4. `cd e2e && pnpm test` — existing E2E tests unaffected
5. Works without Docker

### Decisions

| Decision | Rationale |
| --- | --- |
| Python collector | User preference, consistent with backend stack |
| SQLite over in-memory | Persists across restarts, CLI-inspectable, still zero-config |
| Separate `collector/` directory | Different concern from backend, own pyproject.toml, own process |
| Port 4318 for OTLP ingest | OTLP HTTP standard, drop-in for SigNoz — zero config changes |
| HTTP only, no gRPC | Backend uses `http/protobuf`, frontend uses `http/json` — both on port 4318 |
| Dashboard in Vite app | Reuses Preact, Tailwind, and Wouter. Self-contained under `/observe` for easy future extraction. |
| recharts for metrics, custom waterfall for traces | Recharts suits time-series; trace waterfalls need per-span positioning and hierarchy that charting libs handle poorly |
| `--observe` is opt-in | Doesn't change default `dev.sh` behaviour |
| E2E collector untouched | Stays as Playwright test infra on port 4319 |

### Future Considerations

* **Promote to default**: Once stable, `--observe` could become the default when
  `--signoz` is not specified.
* **Data retention**: 1-hour auto-prune default via `COLLECTOR_RETAIN_MINUTES`
  env var.
* **Dashboard extraction**: If needed later, copy `/observe` pages to a
  standalone Vite app and add CORS to the collector (~15 min task).

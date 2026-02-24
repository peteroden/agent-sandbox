"""FastAPI server for the lightweight OTLP dev collector."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from dev_collector.ingest import (
    CONTENT_TYPE_JSON,
    CONTENT_TYPE_PROTOBUF,
    decode_logs,
    decode_metrics,
    decode_traces,
)
from dev_collector.models import (
    LogRecord,
    MetricName,
    MetricSeries,
    MetricSeriesPoint,
    ServiceName,
    SpanRecord,
    TraceDetail,
    TraceSummary,
)
from dev_collector.storage import Storage

logger = logging.getLogger("dev_collector")

PRUNE_INTERVAL_SECONDS = 300


def _create_storage() -> Storage:
    """Create a Storage instance from environment or defaults."""
    db_path = os.environ.get("COLLECTOR_DB_PATH", Storage._db_path if hasattr(Storage, "_db_path") else None)
    if db_path:
        return Storage(db_path=db_path)
    return Storage()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage storage lifecycle and periodic cleanup."""
    storage = _create_storage()
    await storage.connect()
    app.state.storage = storage
    logger.info("Dev collector started — accepting OTLP on /v1/*")

    prune_task = asyncio.create_task(_periodic_prune(storage))

    yield

    prune_task.cancel()
    try:
        await prune_task
    except asyncio.CancelledError:
        pass
    await storage.close()
    logger.info("Dev collector stopped")


async def _periodic_prune(storage: Storage) -> None:
    """Periodically prune old records."""
    while True:
        await asyncio.sleep(PRUNE_INTERVAL_SECONDS)
        try:
            deleted = await storage.prune()
            if deleted:
                logger.info("Pruned %d old records", deleted)
        except Exception:
            logger.exception("Error during prune")


app = FastAPI(title="Dev OTLP Collector", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_storage(request: Request) -> Storage:
    return request.app.state.storage


def _content_type(request: Request) -> str:
    ct = request.headers.get("content-type", "")
    if "json" in ct:
        return CONTENT_TYPE_JSON
    return CONTENT_TYPE_PROTOBUF


# ── OTLP Ingest Routes ──────────────────────────────────────

@app.post("/v1/traces")
async def ingest_traces(request: Request) -> Response:
    """Accept OTLP trace export requests."""
    body = await request.body()
    storage = _get_storage(request)
    ct = _content_type(request)

    try:
        spans, response_bytes = decode_traces(body, ct)
    except Exception:
        logger.exception("Failed to decode trace payload")
        return JSONResponse(status_code=400, content={"error": "Invalid trace payload"})

    await storage.insert_spans(spans)

    return Response(
        content=response_bytes,
        media_type=CONTENT_TYPE_PROTOBUF,
        status_code=200,
    )


@app.post("/v1/logs")
async def ingest_logs(request: Request) -> Response:
    """Accept OTLP logs export requests."""
    body = await request.body()
    storage = _get_storage(request)
    ct = _content_type(request)

    try:
        logs, response_bytes = decode_logs(body, ct)
    except Exception:
        logger.exception("Failed to decode logs payload")
        return JSONResponse(status_code=400, content={"error": "Invalid logs payload"})

    await storage.insert_logs(logs)

    return Response(
        content=response_bytes,
        media_type=CONTENT_TYPE_PROTOBUF,
        status_code=200,
    )


@app.post("/v1/metrics")
async def ingest_metrics(request: Request) -> Response:
    """Accept OTLP metrics export requests."""
    body = await request.body()
    storage = _get_storage(request)
    ct = _content_type(request)

    try:
        metrics, response_bytes = decode_metrics(body, ct)
    except Exception:
        logger.exception("Failed to decode metrics payload")
        return JSONResponse(status_code=400, content={"error": "Invalid metrics payload"})

    await storage.insert_metrics(metrics)

    return Response(
        content=response_bytes,
        media_type=CONTENT_TYPE_PROTOBUF,
        status_code=200,
    )


# ── Query API Routes ────────────────────────────────────────

@app.get("/api/observe/services", response_model=list[ServiceName])
async def list_services(request: Request) -> list[ServiceName]:
    """List known service names across all signal types."""
    storage = _get_storage(request)
    names = await storage.get_services()
    return [ServiceName(name=n) for n in names]


@app.get("/api/observe/traces", response_model=list[TraceSummary])
async def list_traces(
    request: Request,
    service: str | None = Query(None),
    since: int | None = Query(None, description="Unix nano timestamp"),
    limit: int = Query(50, ge=1, le=1000),
) -> list[TraceSummary]:
    """List recent traces grouped by trace_id."""
    storage = _get_storage(request)
    traces = await storage.get_traces(service=service, since_ns=since, limit=limit)
    return [TraceSummary(**t) for t in traces]


@app.get("/api/observe/traces/{trace_id}", response_model=TraceDetail)
async def get_trace(request: Request, trace_id: str) -> TraceDetail:
    """Get all spans for a specific trace."""
    storage = _get_storage(request)
    spans = await storage.get_trace_spans(trace_id)
    return TraceDetail(
        trace_id=trace_id,
        spans=[SpanRecord(**s) for s in spans],
    )


@app.get("/api/observe/traces/{trace_id}/logs", response_model=list[LogRecord])
async def get_trace_logs(request: Request, trace_id: str) -> list[LogRecord]:
    """Get logs associated with a specific trace."""
    storage = _get_storage(request)
    logs = await storage.get_trace_logs(trace_id)
    return [LogRecord(**lg) for lg in logs]


@app.get("/api/observe/logs", response_model=list[LogRecord])
async def list_logs(
    request: Request,
    service: str | None = Query(None),
    severity: str | None = Query(None),
    trace_id: str | None = Query(None),
    span_id: str | None = Query(None),
    since: int | None = Query(None, description="Unix nano timestamp"),
    limit: int = Query(100, ge=1, le=1000),
) -> list[LogRecord]:
    """List recent logs with optional filters."""
    storage = _get_storage(request)
    logs = await storage.get_logs(
        service=service,
        severity=severity,
        trace_id=trace_id,
        span_id=span_id,
        since_ns=since,
        limit=limit,
    )
    return [LogRecord(**lg) for lg in logs]


@app.get("/api/observe/metrics", response_model=list[MetricName])
async def list_metrics(
    request: Request,
    service: str | None = Query(None),
) -> list[MetricName]:
    """List known metric names with latest values."""
    storage = _get_storage(request)
    names = await storage.get_metric_names(service=service)
    return [MetricName(**m) for m in names]


@app.get("/api/observe/metrics/{name}/series", response_model=MetricSeries)
async def get_metric_series(
    request: Request,
    name: str,
    service: str | None = Query(None),
    since: int | None = Query(None, description="Unix nano timestamp"),
    step: int | None = Query(None, description="Step in nanoseconds"),
) -> MetricSeries:
    """Get time series data for a specific metric."""
    storage = _get_storage(request)
    points = await storage.get_metric_series(
        name=name, service=service, since_ns=since, step_ns=step
    )
    return MetricSeries(
        name=name,
        points=[MetricSeriesPoint(**p) for p in points],
    )


@app.delete("/api/observe/data")
async def delete_data(request: Request) -> dict:
    """Clear all stored telemetry data."""
    storage = _get_storage(request)
    await storage.delete_all()
    return {"status": "ok"}

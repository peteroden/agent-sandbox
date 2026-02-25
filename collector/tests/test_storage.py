"""Tests for the SQLite storage layer."""

from __future__ import annotations

import time

import pytest

from tests.conftest import (
    SAMPLE_DURATION_MS,
    SAMPLE_END_NS,
    SAMPLE_SERVICE_NAME,
    SAMPLE_SPAN_ID,
    SAMPLE_SPAN_NAME,
    SAMPLE_START_NS,
    SAMPLE_TRACE_ID,
)


def _make_span(
    trace_id: str = SAMPLE_TRACE_ID,
    span_id: str = SAMPLE_SPAN_ID,
    name: str = SAMPLE_SPAN_NAME,
    service_name: str = SAMPLE_SERVICE_NAME,
    start_ns: int = SAMPLE_START_NS,
    end_ns: int = SAMPLE_END_NS,
) -> dict:
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": "",
        "name": name,
        "service_name": service_name,
        "kind": 1,
        "status": 0,
        "start_time_unix_nano": start_ns,
        "end_time_unix_nano": end_ns,
        "duration_ms": (end_ns - start_ns) / 1_000_000,
        "attributes": {"http.method": "GET"},
        "events": [],
    }


def _make_log(
    trace_id: str = SAMPLE_TRACE_ID,
    span_id: str = SAMPLE_SPAN_ID,
    service_name: str = SAMPLE_SERVICE_NAME,
    timestamp_ns: int = SAMPLE_START_NS,
) -> dict:
    return {
        "timestamp_unix_nano": timestamp_ns,
        "trace_id": trace_id,
        "span_id": span_id,
        "severity_number": 9,
        "severity_text": "INFO",
        "body": "Test log message",
        "attributes": {},
        "resource_attributes": {},
        "service_name": service_name,
    }


def _make_metric(
    name: str = "http.request.duration",
    service_name: str = SAMPLE_SERVICE_NAME,
    timestamp_ns: int = SAMPLE_START_NS,
    value: float = 42.0,
) -> dict:
    return {
        "timestamp_unix_nano": timestamp_ns,
        "name": name,
        "description": "Request duration",
        "unit": "ms",
        "type": "gauge",
        "value": value,
        "attributes": {},
        "resource_attributes": {},
        "service_name": service_name,
        "exemplar_trace_id": "",
        "exemplar_span_id": "",
    }


@pytest.mark.asyncio
async def test_insert_and_query_spans(storage):
    span = _make_span()
    count = await storage.insert_spans([span])
    assert count == 1

    traces = await storage.get_traces()
    assert len(traces) == 1
    assert traces[0]["trace_id"] == SAMPLE_TRACE_ID
    assert traces[0]["span_count"] == 1


@pytest.mark.asyncio
async def test_get_trace_spans(storage):
    span = _make_span()
    await storage.insert_spans([span])

    spans = await storage.get_trace_spans(SAMPLE_TRACE_ID)
    assert len(spans) == 1
    assert spans[0]["span_id"] == SAMPLE_SPAN_ID
    assert spans[0]["attributes"]["http.method"] == "GET"


@pytest.mark.asyncio
async def test_insert_and_query_logs(storage):
    log = _make_log()
    count = await storage.insert_logs([log])
    assert count == 1

    logs = await storage.get_logs()
    assert len(logs) == 1
    assert logs[0]["severity_text"] == "INFO"


@pytest.mark.asyncio
async def test_get_logs_with_filters(storage):
    await storage.insert_logs([
        _make_log(service_name="svc-a"),
        _make_log(service_name="svc-b"),
    ])

    logs = await storage.get_logs(service="svc-a")
    assert len(logs) == 1
    assert logs[0]["service_name"] == "svc-a"


@pytest.mark.asyncio
async def test_insert_and_query_metrics(storage):
    metric = _make_metric()
    count = await storage.insert_metrics([metric])
    assert count == 1

    names = await storage.get_metric_names()
    assert len(names) == 1
    assert names[0]["name"] == "http.request.duration"
    assert names[0]["latest_value"] == 42.0


@pytest.mark.asyncio
async def test_get_metric_series(storage):
    base_ns = SAMPLE_START_NS
    await storage.insert_metrics([
        _make_metric(timestamp_ns=base_ns, value=10.0),
        _make_metric(timestamp_ns=base_ns + 1_000_000_000, value=20.0),
        _make_metric(timestamp_ns=base_ns + 2_000_000_000, value=30.0),
    ])

    series = await storage.get_metric_series("http.request.duration")
    assert len(series) == 3
    assert series[0]["value"] == 10.0
    assert series[2]["value"] == 30.0


@pytest.mark.asyncio
async def test_get_services(storage):
    await storage.insert_spans([_make_span(service_name="svc-a")])
    await storage.insert_logs([_make_log(service_name="svc-b")])
    await storage.insert_metrics([_make_metric(service_name="svc-c")])

    services = await storage.get_services()
    assert services == ["svc-a", "svc-b", "svc-c"]


@pytest.mark.asyncio
async def test_delete_all(storage):
    await storage.insert_spans([_make_span()])
    await storage.insert_logs([_make_log()])
    await storage.insert_metrics([_make_metric()])

    await storage.delete_all()

    assert await storage.get_traces() == []
    assert await storage.get_logs() == []
    assert await storage.get_metric_names() == []


@pytest.mark.asyncio
async def test_prune_old_records(storage):
    now_ns = int(time.time()) * 1_000_000_000
    old_ns = now_ns - (120 * 60 * 1_000_000_000)  # 2 hours ago

    await storage.insert_spans([_make_span(start_ns=old_ns, end_ns=old_ns + 100_000_000)])
    await storage.insert_spans([_make_span(span_id="new-span", start_ns=now_ns, end_ns=now_ns + 100_000_000)])

    deleted = await storage.prune(retain_minutes=60)
    assert deleted >= 1

    traces = await storage.get_traces()
    assert len(traces) == 1
    assert traces[0]["trace_id"] == SAMPLE_TRACE_ID


@pytest.mark.asyncio
async def test_traces_filter_by_service(storage):
    await storage.insert_spans([
        _make_span(trace_id="trace-a" + "0" * 24, service_name="svc-a"),
        _make_span(trace_id="trace-b" + "0" * 24, span_id="span-b" + "0" * 8, service_name="svc-b"),
    ])

    traces = await storage.get_traces(service="svc-a")
    assert len(traces) == 1
    assert traces[0]["service_name"] == "svc-a"


@pytest.mark.asyncio
async def test_insert_empty_lists(storage):
    assert await storage.insert_spans([]) == 0
    assert await storage.insert_logs([]) == 0
    assert await storage.insert_metrics([]) == 0

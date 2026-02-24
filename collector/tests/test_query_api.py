"""Tests for the query API endpoints."""

from __future__ import annotations

import pytest

from tests.conftest import (
    SAMPLE_SERVICE_NAME,
    SAMPLE_SPAN_ID,
    SAMPLE_SPAN_NAME,
    SAMPLE_START_NS,
    SAMPLE_TRACE_ID,
)


async def _seed_data(storage):
    """Insert sample data for query tests."""
    await storage.insert_spans([{
        "trace_id": SAMPLE_TRACE_ID,
        "span_id": SAMPLE_SPAN_ID,
        "parent_span_id": "",
        "name": SAMPLE_SPAN_NAME,
        "service_name": SAMPLE_SERVICE_NAME,
        "kind": 1,
        "status": 0,
        "start_time_unix_nano": SAMPLE_START_NS,
        "end_time_unix_nano": SAMPLE_START_NS + 100_000_000,
        "duration_ms": 100.0,
        "attributes": {"http.method": "GET"},
        "events": [],
    }])
    await storage.insert_logs([{
        "timestamp_unix_nano": SAMPLE_START_NS,
        "trace_id": SAMPLE_TRACE_ID,
        "span_id": SAMPLE_SPAN_ID,
        "severity_number": 9,
        "severity_text": "INFO",
        "body": "Test log",
        "attributes": {},
        "resource_attributes": {},
        "service_name": SAMPLE_SERVICE_NAME,
    }])
    await storage.insert_metrics([{
        "timestamp_unix_nano": SAMPLE_START_NS,
        "name": "http.request.duration",
        "description": "Duration",
        "unit": "ms",
        "type": "gauge",
        "value": 42.0,
        "attributes": {},
        "resource_attributes": {},
        "service_name": SAMPLE_SERVICE_NAME,
        "exemplar_trace_id": "",
        "exemplar_span_id": "",
    }])


@pytest.mark.asyncio
async def test_list_services(client, storage):
    await _seed_data(storage)
    response = await client.get("/api/observe/services")
    assert response.status_code == 200
    data = response.json()
    names = [s["name"] for s in data]
    assert SAMPLE_SERVICE_NAME in names


@pytest.mark.asyncio
async def test_list_traces(client, storage):
    await _seed_data(storage)
    response = await client.get("/api/observe/traces")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["trace_id"] == SAMPLE_TRACE_ID
    assert data[0]["span_count"] == 1


@pytest.mark.asyncio
async def test_list_traces_filter_service(client, storage):
    await _seed_data(storage)
    response = await client.get("/api/observe/traces", params={"service": "nonexistent"})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_trace_detail(client, storage):
    await _seed_data(storage)
    response = await client.get(f"/api/observe/traces/{SAMPLE_TRACE_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == SAMPLE_TRACE_ID
    assert len(data["spans"]) == 1
    assert data["spans"][0]["name"] == SAMPLE_SPAN_NAME


@pytest.mark.asyncio
async def test_get_trace_logs(client, storage):
    await _seed_data(storage)
    response = await client.get(f"/api/observe/traces/{SAMPLE_TRACE_ID}/logs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["body"] == "Test log"


@pytest.mark.asyncio
async def test_list_logs(client, storage):
    await _seed_data(storage)
    response = await client.get("/api/observe/logs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


@pytest.mark.asyncio
async def test_list_logs_filter_severity(client, storage):
    await _seed_data(storage)
    response = await client.get("/api/observe/logs", params={"severity": "ERROR"})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_metrics(client, storage):
    await _seed_data(storage)
    response = await client.get("/api/observe/metrics")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "http.request.duration"


@pytest.mark.asyncio
async def test_get_metric_series(client, storage):
    await _seed_data(storage)
    response = await client.get("/api/observe/metrics/http.request.duration/series")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "http.request.duration"
    assert len(data["points"]) == 1


@pytest.mark.asyncio
async def test_delete_data(client, storage):
    await _seed_data(storage)
    response = await client.delete("/api/observe/data")
    assert response.status_code == 200

    traces = await client.get("/api/observe/traces")
    assert traces.json() == []

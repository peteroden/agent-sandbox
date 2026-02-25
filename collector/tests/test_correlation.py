"""Tests for trace↔log correlation via trace_id and span_id."""

from __future__ import annotations

import pytest

from tests.conftest import (
    SAMPLE_SERVICE_NAME,
    SAMPLE_SPAN_ID,
    SAMPLE_START_NS,
    SAMPLE_TRACE_ID,
)


@pytest.mark.asyncio
async def test_logs_correlate_with_trace(client, storage):
    """Logs with a trace_id appear when querying that trace's logs."""
    await storage.insert_spans([{
        "trace_id": SAMPLE_TRACE_ID,
        "span_id": SAMPLE_SPAN_ID,
        "parent_span_id": "",
        "name": "root-span",
        "service_name": SAMPLE_SERVICE_NAME,
        "kind": 1,
        "status": 0,
        "start_time_unix_nano": SAMPLE_START_NS,
        "end_time_unix_nano": SAMPLE_START_NS + 50_000_000,
        "duration_ms": 50.0,
        "attributes": {},
        "events": [],
    }])
    await storage.insert_logs([
        {
            "timestamp_unix_nano": SAMPLE_START_NS + 10_000_000,
            "trace_id": SAMPLE_TRACE_ID,
            "span_id": SAMPLE_SPAN_ID,
            "severity_number": 9,
            "severity_text": "INFO",
            "body": "Correlated log",
            "attributes": {},
            "resource_attributes": {},
            "service_name": SAMPLE_SERVICE_NAME,
        },
        {
            "timestamp_unix_nano": SAMPLE_START_NS + 20_000_000,
            "trace_id": "unrelated-trace-id" + "0" * 14,
            "span_id": "unrelated-span",
            "severity_number": 9,
            "severity_text": "INFO",
            "body": "Unrelated log",
            "attributes": {},
            "resource_attributes": {},
            "service_name": SAMPLE_SERVICE_NAME,
        },
    ])

    response = await client.get(f"/api/observe/traces/{SAMPLE_TRACE_ID}/logs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["body"] == "Correlated log"
    assert data[0]["span_id"] == SAMPLE_SPAN_ID


@pytest.mark.asyncio
async def test_logs_filter_by_span_id(client, storage):
    """Logs can be filtered by span_id for span-level correlation."""
    other_span_id = "3a3b3c3d3e3f3031"
    await storage.insert_logs([
        {
            "timestamp_unix_nano": SAMPLE_START_NS,
            "trace_id": SAMPLE_TRACE_ID,
            "span_id": SAMPLE_SPAN_ID,
            "severity_number": 9,
            "severity_text": "INFO",
            "body": "From span A",
            "attributes": {},
            "resource_attributes": {},
            "service_name": SAMPLE_SERVICE_NAME,
        },
        {
            "timestamp_unix_nano": SAMPLE_START_NS,
            "trace_id": SAMPLE_TRACE_ID,
            "span_id": other_span_id,
            "severity_number": 9,
            "severity_text": "INFO",
            "body": "From span B",
            "attributes": {},
            "resource_attributes": {},
            "service_name": SAMPLE_SERVICE_NAME,
        },
    ])

    response = await client.get(
        "/api/observe/logs",
        params={"span_id": SAMPLE_SPAN_ID},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["body"] == "From span A"


@pytest.mark.asyncio
async def test_metrics_with_exemplar_link_to_trace(storage):
    """Metric exemplars carry trace_id and span_id for correlation."""
    await storage.insert_metrics([{
        "timestamp_unix_nano": SAMPLE_START_NS,
        "name": "http.request.duration",
        "description": "Duration",
        "unit": "ms",
        "type": "gauge",
        "value": 150.0,
        "attributes": {},
        "resource_attributes": {},
        "service_name": SAMPLE_SERVICE_NAME,
        "exemplar_trace_id": SAMPLE_TRACE_ID,
        "exemplar_span_id": SAMPLE_SPAN_ID,
    }])

    series = await storage.get_metric_series("http.request.duration")
    assert len(series) == 1
    assert series[0]["value"] == 150.0

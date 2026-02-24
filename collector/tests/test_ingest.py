"""Tests for OTLP ingest decoding (protobuf and JSON)."""

from __future__ import annotations

import json

import pytest
from google.protobuf.json_format import MessageToJson
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.logs.v1.logs_pb2 import LogRecord, ResourceLogs, ScopeLogs
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    Gauge,
    Metric,
    NumberDataPoint,
    ResourceMetrics,
    ScopeMetrics,
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span

from dev_collector.ingest import (
    CONTENT_TYPE_JSON,
    CONTENT_TYPE_PROTOBUF,
    decode_logs,
    decode_metrics,
    decode_traces,
)
from tests.conftest import SAMPLE_SERVICE_NAME, SAMPLE_SPAN_NAME

TRACE_ID_BYTES = bytes.fromhex("0a0b0c0d0e0f1011" + "0" * 16)
SPAN_ID_BYTES = bytes.fromhex("1a1b1c1d1e1f1011")
START_NS = 1_700_000_000_000_000_000
END_NS = 1_700_000_000_100_000_000


def _resource(service_name: str = SAMPLE_SERVICE_NAME) -> Resource:
    return Resource(attributes=[
        KeyValue(key="service.name", value=AnyValue(string_value=service_name)),
    ])


def _build_trace_request() -> ExportTraceServiceRequest:
    span = Span(
        trace_id=TRACE_ID_BYTES,
        span_id=SPAN_ID_BYTES,
        name=SAMPLE_SPAN_NAME,
        kind=Span.SpanKind.SPAN_KIND_SERVER,
        start_time_unix_nano=START_NS,
        end_time_unix_nano=END_NS,
        attributes=[
            KeyValue(key="http.method", value=AnyValue(string_value="GET")),
        ],
    )
    return ExportTraceServiceRequest(
        resource_spans=[
            ResourceSpans(
                resource=_resource(),
                scope_spans=[ScopeSpans(spans=[span])],
            )
        ]
    )


def _build_logs_request() -> ExportLogsServiceRequest:
    log = LogRecord(
        time_unix_nano=START_NS,
        trace_id=TRACE_ID_BYTES,
        span_id=SPAN_ID_BYTES,
        severity_number=9,
        severity_text="INFO",
        body=AnyValue(string_value="Test log message"),
    )
    return ExportLogsServiceRequest(
        resource_logs=[
            ResourceLogs(
                resource=_resource(),
                scope_logs=[ScopeLogs(log_records=[log])],
            )
        ]
    )


def _build_metrics_request() -> ExportMetricsServiceRequest:
    dp = NumberDataPoint(
        time_unix_nano=START_NS,
        as_double=42.0,
    )
    metric = Metric(
        name="http.request.duration",
        description="Request duration",
        unit="ms",
        gauge=Gauge(data_points=[dp]),
    )
    return ExportMetricsServiceRequest(
        resource_metrics=[
            ResourceMetrics(
                resource=_resource(),
                scope_metrics=[ScopeMetrics(metrics=[metric])],
            )
        ]
    )


class TestDecodeTraces:
    def test_protobuf(self):
        request = _build_trace_request()
        body = request.SerializeToString()

        spans, response_bytes = decode_traces(body, CONTENT_TYPE_PROTOBUF)

        assert len(spans) == 1
        assert spans[0]["name"] == SAMPLE_SPAN_NAME
        assert spans[0]["service_name"] == SAMPLE_SERVICE_NAME
        assert spans[0]["trace_id"] == TRACE_ID_BYTES.hex()
        assert spans[0]["span_id"] == SPAN_ID_BYTES.hex()
        assert spans[0]["duration_ms"] == 100.0
        assert spans[0]["attributes"]["http.method"] == "GET"
        assert isinstance(response_bytes, bytes)

    def test_json(self):
        request = _build_trace_request()
        body = MessageToJson(request).encode()

        spans, response_bytes = decode_traces(body, CONTENT_TYPE_JSON)

        assert len(spans) == 1
        assert spans[0]["name"] == SAMPLE_SPAN_NAME
        assert spans[0]["service_name"] == SAMPLE_SERVICE_NAME

    def test_json_hex_trace_ids(self):
        """Browser OTel SDKs send hex-encoded IDs in JSON, not base64."""
        import json
        trace_id_hex = "0a0b0c0d0e0f1011" + "0" * 16
        span_id_hex = "1a1b1c1d1e1f1011"
        body = json.dumps({
            "resourceSpans": [{
                "resource": {"attributes": [
                    {"key": "service.name", "value": {"stringValue": SAMPLE_SERVICE_NAME}},
                ]},
                "scopeSpans": [{
                    "spans": [{
                        "traceId": trace_id_hex,
                        "spanId": span_id_hex,
                        "parentSpanId": "",
                        "name": SAMPLE_SPAN_NAME,
                        "startTimeUnixNano": str(START_NS),
                        "endTimeUnixNano": str(END_NS),
                    }],
                }],
            }],
        }).encode()

        spans, _ = decode_traces(body, CONTENT_TYPE_JSON)

        assert len(spans) == 1
        assert spans[0]["trace_id"] == trace_id_hex
        assert spans[0]["span_id"] == span_id_hex
        assert len(spans[0]["trace_id"]) == 32
        assert len(spans[0]["span_id"]) == 16

    def test_empty_request(self):
        request = ExportTraceServiceRequest()
        body = request.SerializeToString()

        spans, _ = decode_traces(body, CONTENT_TYPE_PROTOBUF)
        assert spans == []


class TestDecodeLogs:
    def test_protobuf(self):
        request = _build_logs_request()
        body = request.SerializeToString()

        logs, response_bytes = decode_logs(body, CONTENT_TYPE_PROTOBUF)

        assert len(logs) == 1
        assert logs[0]["severity_text"] == "INFO"
        assert logs[0]["body"] == "Test log message"
        assert logs[0]["service_name"] == SAMPLE_SERVICE_NAME
        assert logs[0]["trace_id"] == TRACE_ID_BYTES.hex()
        assert isinstance(response_bytes, bytes)

    def test_json(self):
        request = _build_logs_request()
        body = MessageToJson(request).encode()

        logs, _ = decode_logs(body, CONTENT_TYPE_JSON)

        assert len(logs) == 1
        assert logs[0]["body"] == "Test log message"

    def test_empty_request(self):
        request = ExportLogsServiceRequest()
        body = request.SerializeToString()

        logs, _ = decode_logs(body, CONTENT_TYPE_PROTOBUF)
        assert logs == []


class TestDecodeMetrics:
    def test_protobuf(self):
        request = _build_metrics_request()
        body = request.SerializeToString()

        metrics, response_bytes = decode_metrics(body, CONTENT_TYPE_PROTOBUF)

        assert len(metrics) == 1
        assert metrics[0]["name"] == "http.request.duration"
        assert metrics[0]["value"] == 42.0
        assert metrics[0]["type"] == "gauge"
        assert metrics[0]["service_name"] == SAMPLE_SERVICE_NAME
        assert isinstance(response_bytes, bytes)

    def test_json(self):
        request = _build_metrics_request()
        body = MessageToJson(request).encode()

        metrics, _ = decode_metrics(body, CONTENT_TYPE_JSON)

        assert len(metrics) == 1
        assert metrics[0]["name"] == "http.request.duration"

    def test_empty_request(self):
        request = ExportMetricsServiceRequest()
        body = request.SerializeToString()

        metrics, _ = decode_metrics(body, CONTENT_TYPE_PROTOBUF)
        assert metrics == []

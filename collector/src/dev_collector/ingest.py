"""OTLP ingest module — decodes protobuf and JSON payloads into storage-friendly dicts."""

from __future__ import annotations

from google.protobuf.json_format import Parse
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
    ExportLogsServiceResponse,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
    ExportMetricsServiceResponse,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)

CONTENT_TYPE_PROTOBUF = "application/x-protobuf"
CONTENT_TYPE_JSON = "application/json"


def _hex(b: bytes) -> str:
    """Convert bytes to hex string."""
    return b.hex() if b else ""


def _extract_resource_attrs(resource) -> tuple[dict, str]:
    """Extract resource attributes and service name from a resource."""
    attrs = {}
    service_name = ""
    if resource and resource.attributes:
        for kv in resource.attributes:
            key = kv.key
            val = _extract_any_value(kv.value)
            attrs[key] = val
            if key == "service.name":
                service_name = str(val)
    return attrs, service_name


def _extract_any_value(any_value) -> str | int | float | bool:
    """Extract a typed value from an AnyValue protobuf."""
    if any_value.HasField("string_value"):
        return any_value.string_value
    if any_value.HasField("int_value"):
        return any_value.int_value
    if any_value.HasField("double_value"):
        return any_value.double_value
    if any_value.HasField("bool_value"):
        return any_value.bool_value
    return str(any_value)


def _extract_attributes(attrs_list) -> dict:
    """Extract key-value pairs from a repeated KeyValue field."""
    return {kv.key: _extract_any_value(kv.value) for kv in attrs_list}


# ── Traces ───────────────────────────────────────────────────

def decode_traces(body: bytes, content_type: str) -> tuple[list[dict], bytes]:
    """Decode an OTLP trace export request.

    Returns (list of span dicts, serialized response bytes).
    """
    request = _parse_message(ExportTraceServiceRequest, body, content_type)
    spans: list[dict] = []

    for resource_spans in request.resource_spans:
        resource_attrs, service_name = _extract_resource_attrs(resource_spans.resource)

        for scope_spans in resource_spans.scope_spans:
            for span in scope_spans.spans:
                start_ns = span.start_time_unix_nano
                end_ns = span.end_time_unix_nano
                duration_ms = (end_ns - start_ns) / 1_000_000 if end_ns > start_ns else 0.0

                events = []
                for event in span.events:
                    events.append({
                        "name": event.name,
                        "timestamp_unix_nano": event.time_unix_nano,
                        "attributes": _extract_attributes(event.attributes),
                    })

                spans.append({
                    "trace_id": _hex(span.trace_id),
                    "span_id": _hex(span.span_id),
                    "parent_span_id": _hex(span.parent_span_id),
                    "name": span.name,
                    "service_name": service_name,
                    "kind": span.kind,
                    "status": span.status.code if span.status else 0,
                    "start_time_unix_nano": start_ns,
                    "end_time_unix_nano": end_ns,
                    "duration_ms": duration_ms,
                    "attributes": _extract_attributes(span.attributes),
                    "events": events,
                })

    response = ExportTraceServiceResponse()
    return spans, response.SerializeToString()


# ── Logs ─────────────────────────────────────────────────────

def decode_logs(body: bytes, content_type: str) -> tuple[list[dict], bytes]:
    """Decode an OTLP logs export request.

    Returns (list of log dicts, serialized response bytes).
    """
    request = _parse_message(ExportLogsServiceRequest, body, content_type)
    logs: list[dict] = []

    for resource_logs in request.resource_logs:
        resource_attrs, service_name = _extract_resource_attrs(resource_logs.resource)

        for scope_logs in resource_logs.scope_logs:
            for log_record in scope_logs.log_records:
                body_str = ""
                if log_record.body.HasField("string_value"):
                    body_str = log_record.body.string_value
                else:
                    body_str = str(log_record.body)

                logs.append({
                    "timestamp_unix_nano": log_record.time_unix_nano,
                    "trace_id": _hex(log_record.trace_id),
                    "span_id": _hex(log_record.span_id),
                    "severity_number": log_record.severity_number,
                    "severity_text": log_record.severity_text,
                    "body": body_str,
                    "attributes": _extract_attributes(log_record.attributes),
                    "resource_attributes": resource_attrs,
                    "service_name": service_name,
                })

    response = ExportLogsServiceResponse()
    return logs, response.SerializeToString()


# ── Metrics ──────────────────────────────────────────────────

def decode_metrics(body: bytes, content_type: str) -> tuple[list[dict], bytes]:
    """Decode an OTLP metrics export request.

    Returns (list of metric dicts, serialized response bytes).
    """
    request = _parse_message(ExportMetricsServiceRequest, body, content_type)
    metrics: list[dict] = []

    for resource_metrics in request.resource_metrics:
        resource_attrs, service_name = _extract_resource_attrs(resource_metrics.resource)

        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                points = _extract_metric_points(metric)
                for point in points:
                    exemplar_trace_id = point.get("exemplar_trace_id", "")
                    exemplar_span_id = point.get("exemplar_span_id", "")

                    metrics.append({
                        "timestamp_unix_nano": point["timestamp_unix_nano"],
                        "name": metric.name,
                        "description": metric.description,
                        "unit": metric.unit,
                        "type": point["type"],
                        "value": point["value"],
                        "attributes": point.get("attributes", {}),
                        "resource_attributes": resource_attrs,
                        "service_name": service_name,
                        "exemplar_trace_id": exemplar_trace_id,
                        "exemplar_span_id": exemplar_span_id,
                    })

    response = ExportMetricsServiceResponse()
    return metrics, response.SerializeToString()


def _extract_metric_points(metric) -> list[dict]:
    """Extract data points from a metric, handling all metric types."""
    points: list[dict] = []

    if metric.HasField("gauge"):
        for dp in metric.gauge.data_points:
            points.append(_number_data_point(dp, "gauge"))
    elif metric.HasField("sum"):
        for dp in metric.sum.data_points:
            points.append(_number_data_point(dp, "sum"))
    elif metric.HasField("histogram"):
        for dp in metric.histogram.data_points:
            points.append({
                "timestamp_unix_nano": dp.time_unix_nano,
                "type": "histogram",
                "value": dp.sum if dp.sum else 0.0,
                "attributes": _extract_attributes(dp.attributes),
            })
    elif metric.HasField("summary"):
        for dp in metric.summary.data_points:
            points.append({
                "timestamp_unix_nano": dp.time_unix_nano,
                "type": "summary",
                "value": dp.sum,
                "attributes": _extract_attributes(dp.attributes),
            })

    return points


def _number_data_point(dp, metric_type: str) -> dict:
    """Extract a number data point (gauge or sum)."""
    value = dp.as_double if dp.as_double else dp.as_int
    result = {
        "timestamp_unix_nano": dp.time_unix_nano,
        "type": metric_type,
        "value": float(value),
        "attributes": _extract_attributes(dp.attributes),
    }

    if dp.exemplars:
        exemplar = dp.exemplars[0]
        result["exemplar_trace_id"] = _hex(exemplar.trace_id)
        result["exemplar_span_id"] = _hex(exemplar.span_id)

    return result


# ── Helpers ──────────────────────────────────────────────────

def _parse_message(message_class, body: bytes, content_type: str):
    """Parse a protobuf or JSON body into a message."""
    if content_type == CONTENT_TYPE_JSON:
        return Parse(body, message_class())
    msg = message_class()
    msg.ParseFromString(body)
    return msg

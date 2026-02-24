"""Pydantic response models for the collector query API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SpanRecord(BaseModel):
    """A single span stored in the collector."""

    trace_id: str
    span_id: str
    parent_span_id: str = ""
    name: str
    service_name: str = ""
    kind: int = 0
    status: int = 0
    start_time_unix_nano: int
    end_time_unix_nano: int
    duration_ms: float = 0.0
    attributes: dict = Field(default_factory=dict)
    events: list[dict] = Field(default_factory=list)


class LogRecord(BaseModel):
    """A single log record stored in the collector."""

    timestamp_unix_nano: int
    trace_id: str = ""
    span_id: str = ""
    severity_number: int = 0
    severity_text: str = ""
    body: str = ""
    attributes: dict = Field(default_factory=dict)
    resource_attributes: dict = Field(default_factory=dict)
    service_name: str = ""


class MetricRecord(BaseModel):
    """A single metric data point stored in the collector."""

    timestamp_unix_nano: int
    name: str
    description: str = ""
    unit: str = ""
    type: str = ""
    value: float = 0.0
    attributes: dict = Field(default_factory=dict)
    resource_attributes: dict = Field(default_factory=dict)
    service_name: str = ""
    exemplar_trace_id: str = ""
    exemplar_span_id: str = ""


class TraceSummary(BaseModel):
    """Summary of a trace for the trace list view."""

    trace_id: str
    root_span_name: str = ""
    service_name: str = ""
    start_time_unix_nano: int = 0
    duration_ms: float = 0.0
    span_count: int = 0


class TraceDetail(BaseModel):
    """Full trace with all spans."""

    trace_id: str
    spans: list[SpanRecord] = Field(default_factory=list)


class MetricSeriesPoint(BaseModel):
    """A single point in a metric time series."""

    timestamp_unix_nano: int
    value: float


class MetricSeries(BaseModel):
    """Time series data for a single metric."""

    name: str
    description: str = ""
    unit: str = ""
    points: list[MetricSeriesPoint] = Field(default_factory=list)


class MetricName(BaseModel):
    """A known metric name with its latest value."""

    name: str
    description: str = ""
    unit: str = ""
    type: str = ""
    latest_value: float = 0.0
    service_name: str = ""


class ServiceName(BaseModel):
    """A known service name."""

    name: str

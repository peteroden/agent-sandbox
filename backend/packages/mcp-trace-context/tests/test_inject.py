"""Tests for inject function."""

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from mcp_trace_context import inject


@pytest.fixture(autouse=True)
def setup_tracer():
    """Set up a fresh TracerProvider for each test."""
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    yield


class TestInject:
    """Tests for inject() function."""

    def test_returns_empty_dict_without_active_span(self):
        """inject() returns empty dict when no span is active."""
        result = inject()
        assert result == {}

    def test_returns_traceparent_inside_span(self):
        """inject() returns traceparent header inside an active span."""
        tracer = trace.get_tracer("test")
        with tracer.start_as_current_span("test-span"):
            result = inject()

        assert "traceparent" in result
        assert result["traceparent"].startswith("00-")

    def test_traceparent_format(self):
        """inject() returns traceparent in W3C Trace Context format."""
        tracer = trace.get_tracer("test")
        with tracer.start_as_current_span("test-span"):
            result = inject()

        # W3C Trace Context format: 00-{trace_id}-{span_id}-{flags}
        traceparent = result["traceparent"]
        parts = traceparent.split("-")
        assert len(parts) == 4
        assert parts[0] == "00"  # Version
        assert len(parts[1]) == 32  # Trace ID (32 hex chars)
        assert len(parts[2]) == 16  # Span ID (16 hex chars)
        assert len(parts[3]) == 2  # Flags (2 hex chars)

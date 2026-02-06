"""Tests for extract function."""

from opentelemetry.trace import SpanContext, TraceFlags

from mcp_trace_context import extract


class TestExtract:
    """Tests for extract() function."""

    def test_returns_current_context_when_meta_is_none(self):
        """extract() returns current context when meta is None."""
        ctx = extract(None)
        assert ctx is not None

    def test_returns_current_context_when_meta_is_empty(self):
        """extract() returns current context when meta is empty dict."""
        ctx = extract({})
        assert ctx is not None

    def test_extracts_context_from_traceparent(self):
        """extract() extracts valid context from traceparent header."""
        meta = {
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        }
        ctx = extract(meta)
        assert ctx is not None

    def test_extracted_context_has_correct_trace_id(self):
        """Extracted context contains the trace ID from traceparent."""
        trace_id = "0af7651916cd43dd8448eb211c80319c"
        meta = {"traceparent": f"00-{trace_id}-b7ad6b7169203331-01"}

        ctx = extract(meta)

        # Get span from context
        from opentelemetry import trace

        span = trace.get_current_span(ctx)
        span_ctx = span.get_span_context()

        # SpanContext.trace_id is an int, convert to hex for comparison
        extracted_trace_id = format(span_ctx.trace_id, "032x")
        assert extracted_trace_id == trace_id

    def test_extracted_context_has_correct_span_id(self):
        """Extracted context contains the span ID from traceparent."""
        span_id = "b7ad6b7169203331"
        meta = {"traceparent": f"00-0af7651916cd43dd8448eb211c80319c-{span_id}-01"}

        ctx = extract(meta)

        from opentelemetry import trace

        span = trace.get_current_span(ctx)
        span_ctx = span.get_span_context()

        # SpanContext.span_id is an int, convert to hex for comparison
        extracted_span_id = format(span_ctx.span_id, "016x")
        assert extracted_span_id == span_id

    def test_handles_invalid_traceparent_gracefully(self):
        """extract() handles invalid traceparent by returning current context."""
        meta = {"traceparent": "invalid-format"}
        ctx = extract(meta)
        assert ctx is not None

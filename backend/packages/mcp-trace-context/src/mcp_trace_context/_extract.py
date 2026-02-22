"""Extract trace context from MCP _meta field."""

from typing import Any

from opentelemetry import context
from opentelemetry.context import Context
from opentelemetry.propagate import extract as otel_extract


def extract(meta: dict[str, Any] | None) -> Context:
    """Extract trace context from _meta field.

    Extracts traceparent, tracestate, and baggage from the _meta
    dictionary following W3C Trace Context specification.

    Returns current context if meta is None or empty.

    Args:
        meta: Dictionary containing trace context fields.

    Returns:
        OpenTelemetry Context with extracted trace context.

    Example:
        ctx = extract(request._meta)
        with tracer.start_as_current_span("operation", context=ctx):
            ...
    """
    if not meta:
        return context.get_current()

    # Create carrier with trace context fields
    carrier: dict[str, str] = {}
    if "traceparent" in meta:
        carrier["traceparent"] = str(meta["traceparent"])
    if "tracestate" in meta:
        carrier["tracestate"] = str(meta["tracestate"])
    if "baggage" in meta:
        carrier["baggage"] = str(meta["baggage"])

    if carrier:
        return otel_extract(carrier)

    return context.get_current()

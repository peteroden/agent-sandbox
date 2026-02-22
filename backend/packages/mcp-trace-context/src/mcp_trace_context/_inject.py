"""Inject trace context into dict for MCP _meta field."""

from opentelemetry import context
from opentelemetry.propagate import inject as otel_inject


def inject() -> dict[str, str]:
    """Inject current trace context into a dict for _meta field.

    Creates a dictionary suitable for MCP request's _meta field,
    containing traceparent, tracestate, and baggage if present.

    Returns empty dict if no active span or context.

    Returns:
        Dictionary with trace context fields (traceparent, tracestate).

    Example:
        meta = inject()
        await tool.call_tool("my_tool", _meta=meta)
    """
    carrier: dict[str, str] = {}
    otel_inject(carrier, context=context.get_current())
    return carrier

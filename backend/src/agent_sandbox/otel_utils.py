"""OpenTelemetry context utilities for MCP _meta field propagation.

This module provides utilities for extracting and injecting OpenTelemetry
context using MCP's _meta field convention, which works across all transport
types (stdio, HTTP, SSE).

Based on: https://github.com/timvw/fastmcp-otel-langfuse
"""

import asyncio
import functools
import inspect
from typing import Any, Callable, TypeVar

from opentelemetry import context
from opentelemetry.context import Context
from opentelemetry.propagate import get_global_textmap

F = TypeVar("F", bound=Callable[..., Any])


def extract_otel_context_from_meta(meta: dict | None) -> Context:
    """Extract OpenTelemetry context from MCP _meta field.

    The _meta field may contain traceparent, tracestate, and baggage
    following W3C Trace Context specification.

    Args:
        meta: Dictionary containing trace context fields from MCP request

    Returns:
        OpenTelemetry context object with extracted trace context
    """
    if not meta:
        return context.get_current()

    # Create a carrier dict with the trace context fields
    carrier = {}
    if "traceparent" in meta:
        carrier["traceparent"] = meta["traceparent"]
    if "tracestate" in meta:
        carrier["tracestate"] = meta["tracestate"]
    if "baggage" in meta:
        carrier["baggage"] = meta["baggage"]

    # Extract context using OpenTelemetry's propagator
    if carrier:
        propagator = get_global_textmap()
        return propagator.extract(carrier)
    return context.get_current()


def inject_otel_context_to_meta() -> dict:
    """Inject current OpenTelemetry context into _meta field format.

    This creates a dictionary suitable for use in MCP request params._meta
    field, containing traceparent, tracestate, and baggage if present.

    Returns:
        Dictionary with trace context fields for _meta field
    """
    carrier: dict[str, str] = {}
    propagator = get_global_textmap()
    propagator.inject(carrier, context=context.get_current())
    return carrier


def with_otel_context_from_meta(func: F) -> F:
    """Decorator that extracts OpenTelemetry context from MCP request _meta field.

    This decorator expects the decorated function to accept a _meta parameter
    (typically as a keyword argument with default None).

    Usage:
        @mcp.tool()
        @with_otel_context_from_meta
        def my_tool(arg1: str, _meta: dict | None = None) -> str:
            # This function now runs within the propagated trace context
            return "result"

    Args:
        func: The function to decorate

    Returns:
        Decorated function that activates the context from _meta
    """

    # Check if the wrapped function expects _meta in its signature
    sig = inspect.signature(func)
    func_expects_meta = "_meta" in sig.parameters

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Extract _meta from kwargs
        meta = kwargs.get("_meta")
        # Only remove _meta if the function doesn't expect it
        if not func_expects_meta and "_meta" in kwargs:
            del kwargs["_meta"]

        # Extract and activate the context
        ctx = extract_otel_context_from_meta(meta)
        token = context.attach(ctx)

        try:
            return func(*args, **kwargs)
        finally:
            context.detach(token)

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Extract _meta from kwargs
        meta = kwargs.get("_meta")
        # Only remove _meta if the function doesn't expect it
        if not func_expects_meta and "_meta" in kwargs:
            del kwargs["_meta"]

        # Extract and activate the context
        ctx = extract_otel_context_from_meta(meta)
        token = context.attach(ctx)

        try:
            return await func(*args, **kwargs)
        finally:
            context.detach(token)

    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper  # type: ignore[return-value]
    return sync_wrapper  # type: ignore[return-value]

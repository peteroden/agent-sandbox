"""Propagate decorator for MCP tool functions."""

from __future__ import annotations

import asyncio
import functools
import inspect
from collections.abc import Callable
from typing import Any, overload

from opentelemetry import context

from ._extract import extract


@overload
def propagate[F: Callable[..., Any]](func: F) -> F:
    """Decorator without arguments."""
    ...


@overload
def propagate[F: Callable[..., Any]](
    *,
    param: str = "_meta",
) -> Callable[[F], F]:
    """Decorator with arguments."""
    ...


def propagate[F: Callable[..., Any]](
    func: F | None = None,
    *,
    param: str = "_meta",
) -> F | Callable[[F], F]:
    """Decorator that extracts trace context from MCP request.

    Automatically extracts trace context from the specified parameter
    (default: _meta) and activates it for the duration of the function.

    Can be used with or without arguments:

        @propagate
        def my_tool(_meta: dict | None = None): ...

        @propagate(param="context")
        def my_tool(context: dict | None = None): ...

    Args:
        func: The function to decorate (when used without parentheses).
        param: Name of the parameter containing trace context.

    Returns:
        Decorated function that activates propagated context.
    """
    if func is not None:
        # Called without parentheses: @propagate
        return _create_propagate_wrapper(func, param)

    # Called with parentheses: @propagate(...)
    def decorator(fn: F) -> F:
        return _create_propagate_wrapper(fn, param)

    return decorator


def _create_propagate_wrapper[F: Callable[..., Any]](func: F, param: str) -> F:
    """Create a wrapper that extracts and activates trace context."""
    sig = inspect.signature(func)
    func_expects_param = param in sig.parameters

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Extract context from the specified param
        meta = kwargs.get(param)

        # Remove param if function doesn't expect it
        if not func_expects_param and param in kwargs:
            del kwargs[param]

        # Extract and activate context
        ctx = extract(meta)
        token = context.attach(ctx)

        try:
            return func(*args, **kwargs)
        finally:
            context.detach(token)

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Extract context from the specified param
        meta = kwargs.get(param)

        # Remove param if function doesn't expect it
        if not func_expects_param and param in kwargs:
            del kwargs[param]

        # Extract and activate context
        ctx = extract(meta)
        token = context.attach(ctx)

        try:
            return await func(*args, **kwargs)
        finally:
            context.detach(token)

    if asyncio.iscoroutinefunction(func):
        return async_wrapper  # type: ignore[return-value]
    return sync_wrapper  # type: ignore[return-value]

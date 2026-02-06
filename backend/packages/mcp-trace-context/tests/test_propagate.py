"""Tests for propagate decorator."""

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from mcp_trace_context import propagate

# Test traceparent value
TEST_TRACEPARENT = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
TEST_TRACE_ID = "0af7651916cd43dd8448eb211c80319c"


@pytest.fixture(autouse=True)
def setup_tracer():
    """Set up a fresh TracerProvider for each test."""
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    yield


class TestPropagateSyncFunction:
    """Tests for @propagate decorator on sync functions."""

    def test_works_without_meta(self):
        """Decorated function works when _meta is not provided."""

        @propagate
        def my_tool(arg: str, _meta=None) -> str:
            return f"Result: {arg}"

        result = my_tool("test")
        assert result == "Result: test"

    def test_extracts_context_from_meta(self):
        """Decorated function extracts trace context from _meta."""

        @propagate
        def my_tool(arg: str, _meta=None) -> str:
            return f"Result: {arg}"

        meta = {"traceparent": TEST_TRACEPARENT}
        result = my_tool("test", _meta=meta)
        assert result == "Result: test"

    def test_active_span_has_extracted_parent_trace(self):
        """Inside decorated function, current span has extracted trace as parent."""
        captured_trace_id = None

        @propagate
        def my_tool(arg: str, _meta=None) -> str:
            nonlocal captured_trace_id
            tracer = trace.get_tracer("test")
            with tracer.start_as_current_span("inner") as span:
                captured_trace_id = format(
                    span.get_span_context().trace_id, "032x"
                )
            return f"Result: {arg}"

        meta = {"traceparent": TEST_TRACEPARENT}
        my_tool("test", _meta=meta)

        # Inner span should have the same trace ID as the extracted context
        assert captured_trace_id == TEST_TRACE_ID


class TestPropagateAsyncFunction:
    """Tests for @propagate decorator on async functions."""

    @pytest.mark.asyncio
    async def test_works_without_meta(self):
        """Decorated async function works when _meta is not provided."""

        @propagate
        async def my_async_tool(arg: str, _meta=None) -> str:
            return f"Async: {arg}"

        result = await my_async_tool("test")
        assert result == "Async: test"

    @pytest.mark.asyncio
    async def test_extracts_context_from_meta(self):
        """Decorated async function extracts trace context from _meta."""

        @propagate
        async def my_async_tool(arg: str, _meta=None) -> str:
            return f"Async: {arg}"

        meta = {"traceparent": TEST_TRACEPARENT}
        result = await my_async_tool("test", _meta=meta)
        assert result == "Async: test"

    @pytest.mark.asyncio
    async def test_active_span_has_extracted_parent_trace(self):
        """Inside decorated async function, current span has extracted trace."""
        captured_trace_id = None

        @propagate
        async def my_async_tool(arg: str, _meta=None) -> str:
            nonlocal captured_trace_id
            tracer = trace.get_tracer("test")
            with tracer.start_as_current_span("inner") as span:
                captured_trace_id = format(
                    span.get_span_context().trace_id, "032x"
                )
            return f"Async: {arg}"

        meta = {"traceparent": TEST_TRACEPARENT}
        await my_async_tool("test", _meta=meta)

        assert captured_trace_id == TEST_TRACE_ID


class TestPropagateWithCustomParam:
    """Tests for @propagate decorator with custom parameter name."""

    def test_uses_custom_param_name(self):
        """Decorator can use custom parameter name for context extraction."""

        @propagate(param="context")
        def my_tool(arg: str, context=None) -> str:
            return f"Result: {arg}"

        meta = {"traceparent": TEST_TRACEPARENT}
        result = my_tool("test", context=meta)
        assert result == "Result: test"

    def test_removes_param_if_function_does_not_expect_it(self):
        """If function doesn't declare _meta param, decorator removes it."""

        @propagate
        def my_tool(arg: str) -> str:
            return f"Result: {arg}"

        meta = {"traceparent": TEST_TRACEPARENT}
        # Should not raise TypeError about unexpected _meta argument
        result = my_tool("test", _meta=meta)
        assert result == "Result: test"

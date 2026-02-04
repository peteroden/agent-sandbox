"""Tests for OpenTelemetry context utilities.

These tests focus on OUR code logic, not OpenTelemetry library behavior.
"""

import asyncio
import sys
import pytest
from unittest.mock import MagicMock, patch

# === Local Constants ===
TRACEPARENT_HEADER = "traceparent"
TRACESTATE_HEADER = "tracestate"
BAGGAGE_HEADER = "baggage"
SAMPLE_TRACEPARENT = "00-abc-def-01"
SAMPLE_TRACESTATE = "y"
SAMPLE_BAGGAGE = "z"


@pytest.fixture(autouse=True)
def clear_otel_utils_module_cache() -> None:
    """Clear otel_utils module from cache before each test.

    This ensures mock patches work correctly by re-importing the module
    with fresh references to the mocked functions.
    """
    modules_to_remove = [
        key for key in sys.modules if "agent_sandbox.otel_utils" in key
    ]
    for mod in modules_to_remove:
        del sys.modules[mod]


class TestExtractOtelContextFromMeta:
    """Tests for extract_otel_context_from_meta carrier building logic."""

    @pytest.mark.parametrize(
        "meta,expected_keys",
        [
            (None, []),
            ({}, []),
            ({TRACEPARENT_HEADER: SAMPLE_TRACEPARENT}, [TRACEPARENT_HEADER]),
            (
                {TRACEPARENT_HEADER: SAMPLE_TRACEPARENT,
                    TRACESTATE_HEADER: SAMPLE_TRACESTATE},
                [TRACEPARENT_HEADER, TRACESTATE_HEADER],
            ),
            (
                {
                    TRACEPARENT_HEADER: SAMPLE_TRACEPARENT,
                    TRACESTATE_HEADER: SAMPLE_TRACESTATE,
                    BAGGAGE_HEADER: SAMPLE_BAGGAGE,
                },
                [TRACEPARENT_HEADER, TRACESTATE_HEADER, BAGGAGE_HEADER],
            ),
            ({"unrelated": "field"}, []),  # Non-trace fields ignored
        ],
        ids=["none_meta", "empty_meta", "traceparent_only",
             "traceparent_tracestate", "all_headers", "unrelated_field"],
    )
    def test_builds_carrier_from_meta(self, meta: dict[str, str] | None, expected_keys: list[str]) -> None:
        """Verify carrier dict is built correctly from meta fields."""
        with patch("agent_sandbox.otel_utils.get_global_textmap") as mock_textmap:
            mock_propagator = MagicMock()
            mock_textmap.return_value = mock_propagator

            from agent_sandbox.otel_utils import extract_otel_context_from_meta
            extract_otel_context_from_meta(meta)

            if expected_keys:
                mock_propagator.extract.assert_called_once()
                carrier = mock_propagator.extract.call_args[0][0]
                assert sorted(carrier.keys()) == sorted(expected_keys)
            else:
                mock_propagator.extract.assert_not_called()


class TestInjectOtelContextToMeta:
    """Tests for inject_otel_context_to_meta."""

    def test_returns_dict_from_propagator(self) -> None:
        """Verify inject returns a dictionary populated by propagator."""
        with patch("agent_sandbox.otel_utils.get_global_textmap") as mock_textmap:
            mock_propagator = MagicMock()
            mock_textmap.return_value = mock_propagator

            from agent_sandbox.otel_utils import inject_otel_context_to_meta
            result = inject_otel_context_to_meta()

            assert isinstance(result, dict)
            mock_propagator.inject.assert_called_once()


class TestWithOtelContextFromMetaDecorator:
    """Tests for @with_otel_context_from_meta decorator."""

    def test_detects_sync_function(self) -> None:
        """Decorator returns sync wrapper for sync functions."""
        from agent_sandbox.otel_utils import with_otel_context_from_meta

        @with_otel_context_from_meta
        def sync_fn() -> str:
            return "sync"

        assert not asyncio.iscoroutinefunction(sync_fn)
        assert sync_fn() == "sync"

    def test_detects_async_function(self) -> None:
        """Decorator returns async wrapper for async functions."""
        from agent_sandbox.otel_utils import with_otel_context_from_meta

        @with_otel_context_from_meta
        async def async_fn() -> str:
            return "async"

        assert asyncio.iscoroutinefunction(async_fn)

    @pytest.mark.parametrize("has_meta_param", [True, False])
    def test_meta_preservation_based_on_signature_sync(self, has_meta_param: bool) -> None:
        """_meta is preserved only when sync function signature includes it."""
        from agent_sandbox.otel_utils import with_otel_context_from_meta
        received_kwargs: dict[str, object] = {}

        if has_meta_param:

            @with_otel_context_from_meta
            def fn_with_meta(_meta: dict[str, str] | None = None, **kwargs: object) -> None:
                received_kwargs.update({"_meta": _meta, **kwargs})

            fn_with_meta(
                _meta={TRACEPARENT_HEADER: SAMPLE_TRACEPARENT}, other="val")
            assert "_meta" in received_kwargs
            assert received_kwargs["_meta"] == {
                TRACEPARENT_HEADER: SAMPLE_TRACEPARENT}
        else:

            @with_otel_context_from_meta
            def fn_without_meta(**kwargs: object) -> None:
                received_kwargs.update(kwargs)

            fn_without_meta(
                _meta={TRACEPARENT_HEADER: SAMPLE_TRACEPARENT}, other="val")
            assert "_meta" not in received_kwargs
            assert received_kwargs.get("other") == "val"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("has_meta_param", [True, False])
    async def test_meta_preservation_based_on_signature_async(self, has_meta_param: bool) -> None:
        """_meta is preserved only when async function signature includes it."""
        from agent_sandbox.otel_utils import with_otel_context_from_meta
        received_kwargs: dict[str, object] = {}

        if has_meta_param:

            @with_otel_context_from_meta
            async def fn_with_meta(_meta: dict[str, str] | None = None, **kwargs: object) -> None:
                received_kwargs.update({"_meta": _meta, **kwargs})

            await fn_with_meta(_meta={TRACEPARENT_HEADER: SAMPLE_TRACEPARENT}, other="val")
            assert "_meta" in received_kwargs
        else:

            @with_otel_context_from_meta
            async def fn_without_meta(**kwargs: object) -> None:
                received_kwargs.update(kwargs)

            await fn_without_meta(_meta={TRACEPARENT_HEADER: SAMPLE_TRACEPARENT}, other="val")
            assert "_meta" not in received_kwargs

    def test_context_attached_and_detached_sync(self) -> None:
        """Context is attached before and detached after sync function call."""
        with patch("agent_sandbox.otel_utils.context") as mock_context:
            mock_token = MagicMock()
            mock_context.attach.return_value = mock_token

            from agent_sandbox.otel_utils import with_otel_context_from_meta

            @with_otel_context_from_meta
            def my_fn() -> str:
                return "result"

            result = my_fn(_meta={TRACEPARENT_HEADER: SAMPLE_TRACEPARENT})

            assert result == "result"
            mock_context.attach.assert_called_once()
            mock_context.detach.assert_called_once_with(mock_token)

    @pytest.mark.asyncio
    async def test_context_attached_and_detached_async(self) -> None:
        """Context is attached before and detached after async function call."""
        with patch("agent_sandbox.otel_utils.context") as mock_context:
            mock_token = MagicMock()
            mock_context.attach.return_value = mock_token

            from agent_sandbox.otel_utils import with_otel_context_from_meta

            @with_otel_context_from_meta
            async def my_fn() -> str:
                return "async result"

            result = await my_fn(_meta={TRACEPARENT_HEADER: SAMPLE_TRACEPARENT})

            assert result == "async result"
            mock_context.attach.assert_called_once()
            mock_context.detach.assert_called_once_with(mock_token)

    def test_context_detached_on_exception_sync(self) -> None:
        """Context is properly detached even when sync function raises."""
        with patch("agent_sandbox.otel_utils.context") as mock_context:
            mock_token = MagicMock()
            mock_context.attach.return_value = mock_token

            from agent_sandbox.otel_utils import with_otel_context_from_meta

            @with_otel_context_from_meta
            def failing_fn() -> None:
                raise ValueError("test error")

            with pytest.raises(ValueError, match="test error"):
                failing_fn(_meta={TRACEPARENT_HEADER: SAMPLE_TRACEPARENT})

            mock_context.detach.assert_called_once_with(mock_token)

    @pytest.mark.asyncio
    async def test_context_detached_on_exception_async(self) -> None:
        """Context is properly detached even when async function raises."""
        with patch("agent_sandbox.otel_utils.context") as mock_context:
            mock_token = MagicMock()
            mock_context.attach.return_value = mock_token

            from agent_sandbox.otel_utils import with_otel_context_from_meta

            @with_otel_context_from_meta
            async def failing_fn() -> None:
                raise RuntimeError("async error")

            with pytest.raises(RuntimeError, match="async error"):
                await failing_fn(_meta={TRACEPARENT_HEADER: SAMPLE_TRACEPARENT})

            mock_context.detach.assert_called_once_with(mock_token)

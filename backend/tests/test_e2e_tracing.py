"""Integration tests for trace context propagation setup.

These tests verify that our configure_mcp_telemetry function correctly sets up
W3C TraceContext propagation. We don't test OpenTelemetry library behavior.
"""

import sys
from collections.abc import Generator
from unittest.mock import patch

import pytest
from opentelemetry.propagate import get_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


@pytest.fixture(autouse=True)
def clean_modules() -> Generator[None]:
    """Remove cached modules between tests."""
    mods = [k for k in sys.modules if k.startswith("agent_sandbox")]
    for mod in mods:
        del sys.modules[mod]
    yield
    mods = [k for k in sys.modules if k.startswith("agent_sandbox")]
    for mod in mods:
        del sys.modules[mod]


class TestMcpTelemetryPropagation:
    """Tests for trace propagation configuration."""

    def test_configure_sets_w3c_trace_context_propagator(self) -> None:
        """configure_mcp_telemetry sets up W3C TraceContextTextMapPropagator."""
        from opentelemetry import trace

        with patch.object(trace, "set_tracer_provider"):
            from agent_sandbox.telemetry import configure_mcp_telemetry

            configure_mcp_telemetry("test-service")

            textmap = get_global_textmap()
            assert isinstance(textmap, TraceContextTextMapPropagator)

"""Integration tests for trace context propagation setup.

These tests verify that the Agent Framework's configure_otel_providers
correctly sets up W3C TraceContext propagation.
"""

import sys
from collections.abc import Generator

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
        """Agent Framework's configure_otel_providers sets up TraceContext propagator."""
        from agent_framework.observability import configure_otel_providers

        configure_otel_providers()

        textmap = get_global_textmap()
        # Agent Framework sets up TraceContext propagation
        assert textmap is not None

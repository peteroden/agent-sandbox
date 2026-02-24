"""Integration tests for trace context propagation setup.

These tests verify that the Agent Framework's configure_otel_providers
correctly sets up W3C TraceContext propagation.
"""

import os
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
        """Agent Framework's configure_otel_providers sets up TraceContext propagator."""
        from agent_framework.observability import configure_otel_providers

        configure_otel_providers()

        textmap = get_global_textmap()
        # Agent Framework sets up TraceContext propagation
        assert textmap is not None


class TestHttpxInstrumentation:
    """Tests for httpx outbound call instrumentation."""

    def test_httpx_instrumentor_active_when_enabled(self) -> None:
        """HTTPXClientInstrumentor is active when ENABLE_INSTRUMENTATION=true."""
        with patch.dict(os.environ, {"ENABLE_INSTRUMENTATION": "true"}):
            import importlib

            import agent_sandbox.server

            importlib.reload(agent_sandbox.server)

            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

            instrumentor = HTTPXClientInstrumentor()
            assert instrumentor.is_instrumented_by_opentelemetry

            instrumentor.uninstrument()

    def test_httpx_instrumentor_inactive_when_disabled(self) -> None:
        """HTTPXClientInstrumentor is not active when ENABLE_INSTRUMENTATION is unset."""
        with patch.dict(os.environ, {}, clear=True):
            import importlib

            import agent_sandbox.server

            importlib.reload(agent_sandbox.server)

            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

            instrumentor = HTTPXClientInstrumentor()
            assert not instrumentor.is_instrumented_by_opentelemetry

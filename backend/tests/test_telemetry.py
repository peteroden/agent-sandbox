"""Tests for telemetry configuration.

Tests verify our wrapper functions correctly configure OpenTelemetry.
We mock OTel APIs to verify our code calls them correctly - we don't test OTel itself.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.sdk.trace import TracerProvider


class TestConfigureMcpTelemetry:
    """Tests for configure_mcp_telemetry."""

    def test_creates_provider_with_service_name(self) -> None:
        """Creates TracerProvider with correct service name resource."""
        with patch.object(trace, "set_tracer_provider") as mock_set:
            from agent_sandbox.telemetry import configure_mcp_telemetry

            configure_mcp_telemetry("my-service")

            mock_set.assert_called_once()
            provider = mock_set.call_args[0][0]
            assert isinstance(provider, TracerProvider)
            assert provider.resource.attributes.get(
                "service.name") == "my-service"

    @pytest.mark.parametrize("env_value", ["true", "1", "yes", "TRUE", "Yes"])
    def test_adds_console_exporter_when_enabled(self, env_value: str) -> None:
        """Adds console exporter for truthy ENABLE_CONSOLE_EXPORTERS values."""
        with (
            patch.object(trace, "set_tracer_provider") as mock_set,
            patch.dict(
                os.environ, {"ENABLE_CONSOLE_EXPORTERS": env_value}, clear=True),
        ):
            from agent_sandbox.telemetry import configure_mcp_telemetry

            configure_mcp_telemetry("test")

            provider = mock_set.call_args[0][0]
            # Provider should have a span processor added
            assert len(provider._active_span_processor._span_processors) == 1

    @pytest.mark.parametrize("env_value", ["false", "0", "no", ""])
    def test_no_exporter_when_disabled(self, env_value: str) -> None:
        """No console exporter for falsy ENABLE_CONSOLE_EXPORTERS values."""
        with (
            patch.object(trace, "set_tracer_provider") as mock_set,
            patch.dict(
                os.environ, {"ENABLE_CONSOLE_EXPORTERS": env_value}, clear=True),
        ):
            from agent_sandbox.telemetry import configure_mcp_telemetry

            configure_mcp_telemetry("test")

            provider = mock_set.call_args[0][0]
            # No span processors should be added
            assert len(provider._active_span_processor._span_processors) == 0

    def test_adds_otlp_exporter_when_endpoint_set(self) -> None:
        """Adds OTLP exporter when OTEL_EXPORTER_OTLP_ENDPOINT is set."""
        with (
            patch.object(trace, "set_tracer_provider") as mock_set,
            patch.dict(
                os.environ,
                {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4318"},
                clear=True,
            ),
        ):
            from agent_sandbox.telemetry import configure_mcp_telemetry

            configure_mcp_telemetry("test")

            provider = mock_set.call_args[0][0]
            # Provider should have OTLP span processor added
            assert len(provider._active_span_processor._span_processors) == 1

    def test_both_exporters_when_both_enabled(self) -> None:
        """Adds both OTLP and console exporters when both are configured."""
        with (
            patch.object(trace, "set_tracer_provider") as mock_set,
            patch.dict(
                os.environ,
                {
                    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4318",
                    "ENABLE_CONSOLE_EXPORTERS": "true",
                },
                clear=True,
            ),
        ):
            from agent_sandbox.telemetry import configure_mcp_telemetry

            configure_mcp_telemetry("test")

            provider = mock_set.call_args[0][0]
            # Provider should have both span processors added
            assert len(provider._active_span_processor._span_processors) == 2

    def test_sets_w3c_trace_context_propagation(self) -> None:
        """Configures W3C TraceContext propagation."""
        with (
            patch.object(trace, "set_tracer_provider"),
            patch("agent_sandbox.telemetry.set_global_textmap") as mock_set_textmap,
        ):
            from agent_sandbox.telemetry import configure_mcp_telemetry

            configure_mcp_telemetry("test")

            mock_set_textmap.assert_called_once()
            propagator_arg = mock_set_textmap.call_args[0][0]
            assert isinstance(propagator_arg, TraceContextTextMapPropagator)


class TestInstrumentMcpApp:
    """Tests for instrument_mcp_app."""

    def test_calls_starlette_instrumentor(self) -> None:
        """Calls StarletteInstrumentor.instrument() when not already instrumented."""
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = False

        with patch(
            "opentelemetry.instrumentation.starlette.StarletteInstrumentor",
            return_value=mock_instrumentor,
        ):
            from agent_sandbox.telemetry import instrument_mcp_app

            instrument_mcp_app()

            mock_instrumentor.instrument.assert_called_once()

    def test_skips_instrumentation_when_already_instrumented(self) -> None:
        """Skips instrumentation when already instrumented by OpenTelemetry."""
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = True

        with patch(
            "opentelemetry.instrumentation.starlette.StarletteInstrumentor",
            return_value=mock_instrumentor,
        ):
            from agent_sandbox.telemetry import instrument_mcp_app

            instrument_mcp_app()

            mock_instrumentor.instrument.assert_not_called()


class TestGetTracer:
    """Tests for get_tracer."""

    def test_returns_tracer_named_agent_sandbox(self) -> None:
        """Returns tracer with 'agent_sandbox' instrumentation scope."""
        mock_provider = MagicMock()

        with patch.object(trace, "get_tracer_provider", return_value=mock_provider):
            from agent_sandbox.telemetry import get_tracer

            get_tracer()

            mock_provider.get_tracer.assert_called_once()
            assert mock_provider.get_tracer.call_args[0][0] == "agent_sandbox"

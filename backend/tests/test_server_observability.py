"""Tests for server observability configuration."""

import os
import sys
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def clean_server_module() -> Generator[None]:
    """Remove cached server module between tests."""
    mods = [k for k in sys.modules if k.startswith("agent_sandbox.server")]
    for mod in mods:
        del sys.modules[mod]
    yield
    mods = [k for k in sys.modules if k.startswith("agent_sandbox.server")]
    for mod in mods:
        del sys.modules[mod]


@pytest.fixture
def mock_dependencies() -> Generator[MagicMock]:
    """Mock external dependencies for module import."""
    mock_configure = MagicMock()
    mock_httpx = MagicMock()
    mock_instrument = MagicMock()

    with (
        patch("agent_framework.MCPStreamableHTTPTool", MagicMock()),
        patch("agent_sandbox.telemetry.configure_mcp_telemetry", mock_configure),
        patch("agent_sandbox.telemetry.instrument_mcp_app", mock_instrument),
        patch(
            "opentelemetry.instrumentation.httpx.HTTPXClientInstrumentor",
            MagicMock(return_value=mock_httpx),
        ),
    ):
        yield {
            "configure_telemetry": mock_configure,
            "instrument_app": mock_instrument,
            "httpx_instrumentor": mock_httpx,
        }


class TestServerObservability:
    """Tests for server.py observability configuration."""

    @pytest.mark.parametrize(
        ("env", "should_configure"),
        [
            (
                {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4318",
                    "LLM_PROVIDER": "mock"},
                True,
            ),
            ({"LLM_PROVIDER": "mock"}, False),
        ],
        ids=["instrumentation_enabled", "instrumentation_disabled"],
    )
    def test_otel_configuration(
        self, mock_dependencies: dict, env: dict, should_configure: bool
    ) -> None:
        """configure_mcp_telemetry called only when OTEL_EXPORTER_OTLP_ENDPOINT is set."""
        with patch.dict(os.environ, env, clear=True):
            import agent_sandbox.server  # noqa: F401

            if should_configure:
                mock_dependencies["configure_telemetry"].assert_called_once()
                mock_dependencies["httpx_instrumentor"].instrument.assert_called_once(
                )
            else:
                mock_dependencies["configure_telemetry"].assert_not_called()

"""Tests for demo MCP App server."""

import json

import pytest

from agent_sandbox.demo_app_mcp_server import (
    EMBEDDED_VIEW_HTML,
    _get_system_stats,
    mcp,
    system_stats,
    view,
)

MCP_SERVER_NAME = "Demo App"
REQUIRED_STAT_KEYS = [
    "cpu_percent",
    "memory_percent",
    "memory_used_gb",
    "memory_total_gb",
    "disk_percent",
    "disk_used_gb",
    "disk_total_gb",
    "uptime",
    "platform",
    "hostname",
    "python_version",
]


class TestMCPServerConfiguration:
    """Tests for MCP server setup."""

    def test_mcp_server_has_correct_name(self) -> None:
        """MCP server should have the expected name."""
        assert mcp.name == MCP_SERVER_NAME


class TestGetSystemStats:
    """Tests for the _get_system_stats helper."""

    def test_returns_all_required_keys(self) -> None:
        """Stats dict should contain all expected keys."""
        stats = _get_system_stats()
        for key in REQUIRED_STAT_KEYS:
            assert key in stats, f"Missing key: {key}"

    @pytest.mark.parametrize(
        "key",
        ["cpu_percent", "memory_percent", "disk_percent"],
        ids=["cpu", "memory", "disk"],
    )
    def test_percentage_values_in_range(self, key: str) -> None:
        """Percentage values should be between 0 and 100."""
        stats = _get_system_stats()
        assert 0.0 <= stats[key] <= 100.0

    def test_uptime_format(self) -> None:
        """Uptime should match the expected format."""
        stats = _get_system_stats()
        assert "h " in stats["uptime"]
        assert "m " in stats["uptime"]
        assert stats["uptime"].endswith("s")


class TestSystemStatsTool:
    """Tests for the system_stats tool function."""

    def test_returns_valid_json(self) -> None:
        """Tool should return a valid JSON string."""
        result = system_stats()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_json_contains_all_keys(self) -> None:
        """Tool JSON output should contain all required keys."""
        result = system_stats()
        parsed = json.loads(result)
        for key in REQUIRED_STAT_KEYS:
            assert key in parsed, f"Missing key: {key}"


class TestViewResource:
    """Tests for the view HTML resource."""

    def test_returns_html(self) -> None:
        """View resource should return HTML content."""
        html = view()
        assert html.startswith("<!DOCTYPE html>")

    def test_html_uses_ext_apps_sdk(self) -> None:
        """View should import App from @modelcontextprotocol/ext-apps."""
        html = view()
        assert "@modelcontextprotocol/ext-apps" in html
        assert "app.callServerTool" in html
        assert "app.ontoolresult" in html
        assert "app.connect()" in html

    def test_html_contains_gauge_elements(self) -> None:
        """View should contain gauge UI elements."""
        html = view()
        assert "gauge-fill" in html
        assert "cpu-val" in html
        assert "mem-val" in html
        assert "disk-val" in html

    def test_html_contains_refresh_button(self) -> None:
        """View should have a refresh button."""
        html = view()
        assert "refresh-btn" in html

    def test_embedded_html_matches_resource(self) -> None:
        """Resource function should return the embedded HTML constant."""
        assert view() == EMBEDDED_VIEW_HTML

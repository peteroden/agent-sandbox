"""Tests for text MCP server and echo_text tool."""

import pytest

from agent_sandbox.text_mcp_server import echo_text, mcp

# === Local Constants ===
MCP_SERVER_NAME = "Text Tools"


class TestMCPServerConfiguration:
    """Tests for MCP server setup."""

    def test_mcp_server_has_correct_name(self) -> None:
        """MCP server should have the expected name."""
        assert mcp.name == MCP_SERVER_NAME


class TestEchoTextTool:
    """Tests for the echo_text tool function."""

    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("Hello, world!", "Hello, world!"),
            ("", ""),
            ("Test with émojis 🎉 and symbols @#$%",
             "Test with émojis 🎉 and symbols @#$%"),
        ],
        ids=["normal_message", "empty_string", "special_characters"],
    )
    def test_echo_text(self, message: str, expected: str) -> None:
        """echo_text should return the message as-is."""
        result = echo_text(message)
        assert result == expected

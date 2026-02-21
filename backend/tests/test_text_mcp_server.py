"""Tests for text MCP server and echo_text tool."""

import pytest

from agent_sandbox.text_mcp_server import echo_text, mcp

# === Local Constants ===
MCP_SERVER_NAME = "Text Tools"
ECHO_PREFIX = "Echo: "


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
            ("Hello, world!", f"{ECHO_PREFIX}Hello, world!"),
            ("", f"{ECHO_PREFIX}"),
            ("Test with émojis 🎉 and symbols @#$%",
             f"{ECHO_PREFIX}Test with émojis 🎉 and symbols @#$%"),
        ],
        ids=["normal_message", "empty_string", "special_characters"],
    )
    def test_echo_text(self, message: str, expected: str) -> None:
        """echo_text should return message with 'Echo: ' prefix."""
        result = echo_text(message)
        assert result == expected

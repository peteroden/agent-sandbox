"""Tests for text MCP server and echo_text tool."""

from agent_sandbox.text_mcp_server import echo_text, mcp


class TestMCPServerConfiguration:
    """Tests for MCP server setup."""

    def test_mcp_server_has_correct_name(self) -> None:
        """MCP server should have the expected name."""
        assert mcp.name == "Text Tools"

    def test_echo_text_tool_is_registered(self) -> None:
        """echo_text tool should be registered with the MCP server."""
        tool_names = [tool.name for tool in mcp._tool_manager._tools.values()]
        assert "echo_text" in tool_names


class TestEchoTextTool:
    """Tests for the echo_text tool function."""

    def test_echo_text_returns_message_with_prefix(self) -> None:
        """echo_text should return message with 'Echo: ' prefix."""
        result = echo_text.fn("Hello, world!")
        assert result == "Echo: Hello, world!"

    def test_echo_text_handles_empty_string(self) -> None:
        """echo_text should handle empty string input."""
        result = echo_text.fn("")
        assert result == "Echo: "

    def test_echo_text_preserves_special_characters(self) -> None:
        """echo_text should preserve special characters in message."""
        result = echo_text.fn("Test with émojis 🎉 and symbols @#$%")
        assert result == "Echo: Test with émojis 🎉 and symbols @#$%"

"""Tests for number MCP server and math tools."""

from agent_sandbox.number_mcp_server import add_numbers, mcp, subtract_numbers


class TestMCPServerConfiguration:
    """Tests for MCP server setup."""

    def test_mcp_server_has_correct_name(self) -> None:
        """MCP server should have the expected name."""
        assert mcp.name == "Number Tools"

    def test_add_numbers_tool_is_registered(self) -> None:
        """add_numbers tool should be registered with the MCP server."""
        tool_names = [tool.name for tool in mcp._tool_manager._tools.values()]
        assert "add_numbers" in tool_names

    def test_subtract_numbers_tool_is_registered(self) -> None:
        """subtract_numbers tool should be registered with the MCP server."""
        tool_names = [tool.name for tool in mcp._tool_manager._tools.values()]
        assert "subtract_numbers" in tool_names


class TestAddNumbersTool:
    """Tests for the add_numbers tool function."""

    def test_add_numbers_returns_sum_of_two_positive_numbers(self) -> None:
        """add_numbers should return the sum of two positive integers."""
        result = add_numbers.fn(5, 3)
        assert result == 8

    def test_add_numbers_handles_negative_numbers(self) -> None:
        """add_numbers should handle negative numbers correctly."""
        result = add_numbers.fn(-5, 3)
        assert result == -2

    def test_add_numbers_handles_zero(self) -> None:
        """add_numbers should handle zero correctly."""
        result = add_numbers.fn(0, 10)
        assert result == 10

    def test_add_numbers_handles_large_numbers(self) -> None:
        """add_numbers should handle large numbers correctly."""
        result = add_numbers.fn(1_000_000, 2_000_000)
        assert result == 3_000_000


class TestSubtractNumbersTool:
    """Tests for the subtract_numbers tool function."""

    def test_subtract_numbers_returns_difference(self) -> None:
        """subtract_numbers should return the difference of two integers."""
        result = subtract_numbers.fn(10, 3)
        assert result == 7

    def test_subtract_numbers_handles_negative_result(self) -> None:
        """subtract_numbers should handle negative results correctly."""
        result = subtract_numbers.fn(3, 10)
        assert result == -7

    def test_subtract_numbers_handles_negative_numbers(self) -> None:
        """subtract_numbers should handle negative input numbers correctly."""
        result = subtract_numbers.fn(-5, -3)
        assert result == -2

    def test_subtract_numbers_handles_zero(self) -> None:
        """subtract_numbers should handle zero correctly."""
        result = subtract_numbers.fn(10, 0)
        assert result == 10

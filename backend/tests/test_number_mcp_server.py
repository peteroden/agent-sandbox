"""Tests for number MCP server and math tools."""

import pytest

from agent_sandbox.number_mcp_server import add_numbers, mcp, subtract_numbers

# === Local Constants ===
MCP_SERVER_NAME = "Number Tools"


class TestMCPServerConfiguration:
    """Tests for MCP server setup."""

    def test_mcp_server_has_correct_name(self) -> None:
        """MCP server should have the expected name."""
        assert mcp.name == MCP_SERVER_NAME


class TestAddNumbersTool:
    """Tests for the add_numbers tool function."""

    @pytest.mark.parametrize(
        ("a", "b", "expected"),
        [
            (5, 3, 8),
            (-5, 3, -2),
            (0, 10, 10),
            (1_000_000, 2_000_000, 3_000_000),
        ],
        ids=["positive", "negative", "zero", "large"],
    )
    def test_add_numbers(self, a: int, b: int, expected: int) -> None:
        """add_numbers should return the sum of two integers."""
        result = add_numbers(a, b)
        assert result == expected


class TestSubtractNumbersTool:
    """Tests for the subtract_numbers tool function."""

    @pytest.mark.parametrize(
        ("a", "b", "expected"),
        [
            (10, 3, 7),
            (3, 10, -7),
            (-5, -3, -2),
            (10, 0, 10),
        ],
        ids=["positive_result", "negative_result",
             "negative_inputs", "subtract_zero"],
    )
    def test_subtract_numbers(self, a: int, b: int, expected: int) -> None:
        """subtract_numbers should return the difference of two integers."""
        result = subtract_numbers(a, b)
        assert result == expected

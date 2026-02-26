"""Tests for mock utility functions.

Pure function tests for shared mock utilities.
"""

import pytest

from agent_sandbox.agents.mock_utils import (
    _normalize_result,
    detect_tool_request,
    parse_integers,
)

# === Local Test Constants ===
TEST_TOOL_NAME_ADD = "add_numbers"
TEST_TOOL_NAME_ECHO = "echo_text"


class TestParseIntegers:
    """Tests for parse_integers function."""

    @pytest.mark.parametrize(
        ("input_text", "expected"),
        [
            ("5 3", [5, 3]),
            ("5, 3", [5, 3]),
            ("-5 3", [-5, 3]),
            ("add 10 and 20 together", [10, 20]),
            ("5", [5]),
            ("hello world", []),
            ("", []),
            ("   ", []),
            ("-100 -200", [-100, -200]),
        ],
        ids=[
            "space_separated",
            "comma_separated",
            "negative_first",
            "embedded_in_text",
            "single_number",
            "no_numbers",
            "empty_string",
            "whitespace_only",
            "both_negative",
        ],
    )
    def test_parse_integers(self, input_text: str, expected: list[int]) -> None:
        """parse_integers extracts all integers from string."""
        result = parse_integers(input_text)
        assert result == expected


class TestDetectToolRequest:
    """Tests for detect_tool_request function."""

    @pytest.mark.parametrize(
        ("message", "tool_names", "expected_tool", "expected_remaining"),
        [
            (f"use {TEST_TOOL_NAME_ADD} 5 3", [
             TEST_TOOL_NAME_ADD], TEST_TOOL_NAME_ADD, "5 3"),
            (
                f"use {TEST_TOOL_NAME_ECHO} hello world",
                [TEST_TOOL_NAME_ECHO],
                TEST_TOOL_NAME_ECHO,
                "hello world",
            ),
            ("no tool here", [TEST_TOOL_NAME_ADD,
             TEST_TOOL_NAME_ECHO], None, "no tool here"),
            (f"use {TEST_TOOL_NAME_ADD}", [
             TEST_TOOL_NAME_ADD], TEST_TOOL_NAME_ADD, ""),
            (
                f"USE {TEST_TOOL_NAME_ADD.upper()} 1 2",
                [TEST_TOOL_NAME_ADD],
                TEST_TOOL_NAME_ADD,
                "1 2",
            ),
            ("use unknown_tool arg", [
             TEST_TOOL_NAME_ADD], None, "use unknown_tool arg"),
            ("some text before use add_numbers 5 3", [
             TEST_TOOL_NAME_ADD], TEST_TOOL_NAME_ADD, "5 3"),
            ("use echo hello world", [
             TEST_TOOL_NAME_ECHO], TEST_TOOL_NAME_ECHO, "hello world"),
            ("use add 5 3", [
             TEST_TOOL_NAME_ADD], TEST_TOOL_NAME_ADD, "5 3"),
        ],
        ids=[
            "add_tool",
            "echo_tool",
            "no_match",
            "no_args",
            "case_insensitive",
            "unknown_tool",
            "tool_mid_sentence",
            "echo_alias",
            "add_alias",
        ],
    )
    def test_detect_tool_request(
        self,
        message: str,
        tool_names: list[str],
        expected_tool: str | None,
        expected_remaining: str,
    ) -> None:
        """detect_tool_request correctly identifies tool patterns."""
        tool_name, remaining = detect_tool_request(message, tool_names)
        assert tool_name == expected_tool
        assert remaining == expected_remaining

    def test_empty_tool_names_list(self) -> None:
        """Returns None when no tools available."""
        tool_name, remaining = detect_tool_request(
            f"use {TEST_TOOL_NAME_ADD} 5", [])
        assert tool_name is None
        assert remaining == f"use {TEST_TOOL_NAME_ADD} 5"


class TestNormalizeResult:
    """Tests for _normalize_result function."""

    def test_plain_string(self) -> None:
        assert _normalize_result("hello") == "hello"

    def test_mcp_dict_list(self) -> None:
        """MCP-style [{"type":"text","text":"8"}] returns '8'."""
        assert _normalize_result([{"type": "text", "text": "8"}]) == "8"

    def test_content_object_list(self) -> None:
        """Framework Content objects with .text attribute are extracted."""
        from agent_framework import Content

        # Content.from_function_result stores the result, but the framework
        # wraps tool outputs in Content objects with a .text attribute
        obj = Content.from_text(text="Echo: hi")
        assert _normalize_result([obj]) == "Echo: hi"

    def test_single_content_object(self) -> None:
        """Single Content object (not in list) is extracted."""
        from agent_framework import Content

        obj = Content.from_text(text="42")
        assert _normalize_result(obj) == "42"

    def test_string_list(self) -> None:
        assert _normalize_result(["hello", "world"]) == "hello world"

    def test_integer_fallback(self) -> None:
        assert _normalize_result(42) == "42"

"""Tests for MockChatClient.

Tests the BaseChatClient implementation for mock LLM responses.
"""

from collections.abc import MutableSequence
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from agent_framework import ChatMessage, ChatResponse, ChatResponseUpdate, Content, Role

from agent_sandbox.agents.mock_chat_client import MockChatClient

# === Local Test Constants ===
MOCK_PREFIX = "[Mock] "
TEST_MESSAGE = "hello world"
TEST_TOOL_NAME_ADD = "add_numbers"
TEST_TOOL_NAME_ECHO = "echo_text"
TEST_TOOL_PARAM_A = "a"
TEST_TOOL_PARAM_B = "b"
TEST_TOOL_PARAM_TEXT = "text"


def make_messages(text: str) -> MutableSequence[ChatMessage]:
    """Create a mutable sequence of messages with a single user message."""
    return [ChatMessage(role=Role.USER, text=text)]


def make_options() -> dict[str, Any]:
    """Create empty options dict for chat client calls."""
    return {}


@pytest.fixture
def mock_chat_client() -> MockChatClient:
    """Create a MockChatClient instance for testing."""
    return MockChatClient()


class TestMockChatClientResponse:
    """Tests for MockChatClient response generation."""

    @pytest.mark.asyncio
    async def test_get_response_returns_chat_response(
        self, mock_chat_client: MockChatClient
    ) -> None:
        """_inner_get_response() returns a ChatResponse object."""
        messages = make_messages(TEST_MESSAGE)

        response = await mock_chat_client._inner_get_response(
            messages=messages, options=make_options()
        )

        assert isinstance(response, ChatResponse)

    @pytest.mark.asyncio
    async def test_get_response_contains_prefix(
        self, mock_chat_client: MockChatClient
    ) -> None:
        """Response text starts with the mock prefix."""
        messages = make_messages(TEST_MESSAGE)

        response = await mock_chat_client._inner_get_response(
            messages=messages, options=make_options()
        )

        # Get text from response - either direct text or from messages
        response_text = response.text or ""
        if not response_text and response.messages:
            first_msg = response.messages[0] if response.messages else None
            response_text = first_msg.text if first_msg else ""

        assert response_text.startswith(MOCK_PREFIX)

    @pytest.mark.asyncio
    async def test_get_response_echoes_message(
        self, mock_chat_client: MockChatClient
    ) -> None:
        """Response echoes the user message."""
        messages = make_messages(TEST_MESSAGE)

        response = await mock_chat_client._inner_get_response(
            messages=messages, options=make_options()
        )

        response_text = response.text or ""
        if not response_text and response.messages:
            first_msg = response.messages[0] if response.messages else None
            response_text = first_msg.text if first_msg else ""

        assert TEST_MESSAGE in response_text

    @pytest.mark.asyncio
    async def test_get_streaming_response_yields_updates(
        self, mock_chat_client: MockChatClient
    ) -> None:
        """_inner_get_streaming_response() yields ChatResponseUpdate objects."""
        messages = make_messages(TEST_MESSAGE)

        updates = [
            update
            async for update in mock_chat_client._inner_get_streaming_response(
                messages=messages, options=make_options()
            )
        ]

        assert len(updates) >= 1
        assert all(isinstance(u, ChatResponseUpdate) for u in updates)

    @pytest.mark.asyncio
    async def test_get_streaming_response_contains_message(
        self, mock_chat_client: MockChatClient
    ) -> None:
        """Streaming updates contain the user message."""
        messages = make_messages(TEST_MESSAGE)

        updates = [
            update
            async for update in mock_chat_client._inner_get_streaming_response(
                messages=messages, options=make_options()
            )
        ]

        all_text = "".join(u.text or "" for u in updates)
        assert TEST_MESSAGE in all_text

    @pytest.mark.asyncio
    async def test_get_response_handles_empty_messages(
        self, mock_chat_client: MockChatClient
    ) -> None:
        """Handles empty message list gracefully."""
        messages: MutableSequence[ChatMessage] = []

        response = await mock_chat_client._inner_get_response(
            messages=messages, options=make_options()
        )

        assert isinstance(response, ChatResponse)
        response_text = response.text or ""
        if not response_text and response.messages:
            first_msg = response.messages[0] if response.messages else None
            response_text = first_msg.text if first_msg else ""
        # Should have some default response
        assert MOCK_PREFIX in response_text or "No message" in response_text


class TestMockChatClientToolDetection:
    """Tests for MockChatClient tool detection."""

    @pytest.fixture
    def mock_tool_provider(self) -> MagicMock:
        """Create a mock tool provider with add_numbers and echo_text tools."""
        tool = MagicMock()

        # Create add_numbers function mock
        add_func = MagicMock()
        add_func.name = TEST_TOOL_NAME_ADD
        add_func.parameters = MagicMock(
            return_value={
                "type": "object",
                "properties": {
                    TEST_TOOL_PARAM_A: {"type": "integer"},
                    TEST_TOOL_PARAM_B: {"type": "integer"},
                },
                "required": [TEST_TOOL_PARAM_A, TEST_TOOL_PARAM_B],
            }
        )

        # Create echo_text function mock
        echo_func = MagicMock()
        echo_func.name = TEST_TOOL_NAME_ECHO
        echo_func.parameters = MagicMock(
            return_value={
                "type": "object",
                "properties": {
                    TEST_TOOL_PARAM_TEXT: {"type": "string"},
                },
                "required": [TEST_TOOL_PARAM_TEXT],
            }
        )

        tool.functions = [add_func, echo_func]
        tool.call_tool = AsyncMock(return_value="result")
        return tool

    @pytest.mark.parametrize(
        ("message", "expected_tool", "expected_args"),
        [
            (
                f"use {TEST_TOOL_NAME_ADD} 5 3",
                TEST_TOOL_NAME_ADD,
                {TEST_TOOL_PARAM_A: 5, TEST_TOOL_PARAM_B: 3},
            ),
            (
                f"use {TEST_TOOL_NAME_ECHO} hello",
                TEST_TOOL_NAME_ECHO,
                {TEST_TOOL_PARAM_TEXT: "hello"},
            ),
            ("no tool here", None, None),
        ],
        ids=["add_numbers", "echo_text", "no_tool"],
    )
    @pytest.mark.asyncio
    async def test_tool_detection_patterns(
        self,
        mock_tool_provider: MagicMock,
        message: str,
        expected_tool: str | None,
        expected_args: dict[str, Any] | None,
    ) -> None:
        """Tool detection patterns are correctly identified."""
        client = MockChatClient(tools=[mock_tool_provider])
        messages = make_messages(message)

        updates = [
            update
            async for update in client._inner_get_streaming_response(
                messages=messages, options=make_options()
            )
        ]

        if expected_tool is None:
            # No tool call should be emitted
            function_calls = [
                c
                for u in updates
                if u.contents
                for c in u.contents
                if getattr(c, "type", None) == "function_call"
            ]
            assert len(function_calls) == 0
        else:
            # Tool call should be emitted
            function_calls = [
                c
                for u in updates
                if u.contents
                for c in u.contents
                if getattr(c, "type", None) == "function_call"
            ]
            assert len(function_calls) >= 1
            fc = function_calls[0]
            assert fc.name == expected_tool
            mock_tool_provider.call_tool.assert_called_once()
            call_args = mock_tool_provider.call_tool.call_args
            assert call_args[0][0] == expected_tool
            for key, value in expected_args.items():
                assert key in call_args[1]
                assert call_args[1][key] == value

    @pytest.mark.asyncio
    async def test_emits_function_call_content(
        self, mock_tool_provider: MagicMock
    ) -> None:
        """Emits Content.from_function_call when tool detected."""
        client = MockChatClient(tools=[mock_tool_provider])
        messages = make_messages(f"use {TEST_TOOL_NAME_ADD} 5 3")

        updates = [
            update
            async for update in client._inner_get_streaming_response(
                messages=messages, options=make_options()
            )
        ]

        function_calls = [
            c
            for u in updates
            if u.contents
            for c in u.contents
            if getattr(c, "type", None) == "function_call"
        ]
        assert len(function_calls) >= 1
        fc = function_calls[0]
        assert fc.name == TEST_TOOL_NAME_ADD
        assert fc.call_id is not None

    @pytest.mark.asyncio
    async def test_emits_function_result_content(
        self, mock_tool_provider: MagicMock
    ) -> None:
        """Emits Content.from_function_result after tool execution."""
        mock_tool_provider.call_tool.return_value = "8"
        client = MockChatClient(tools=[mock_tool_provider])
        messages = make_messages(f"use {TEST_TOOL_NAME_ADD} 5 3")

        updates = [
            update
            async for update in client._inner_get_streaming_response(
                messages=messages, options=make_options()
            )
        ]

        function_results = [
            c
            for u in updates
            if u.contents
            for c in u.contents
            if getattr(c, "type", None) == "function_result"
        ]
        assert len(function_results) >= 1
        fr = function_results[0]
        assert "8" in fr.result

    @pytest.mark.asyncio
    async def test_call_id_matches(self, mock_tool_provider: MagicMock) -> None:
        """call_id matches between function_call and function_result."""
        client = MockChatClient(tools=[mock_tool_provider])
        messages = make_messages(f"use {TEST_TOOL_NAME_ADD} 5 3")

        updates = [
            update
            async for update in client._inner_get_streaming_response(
                messages=messages, options=make_options()
            )
        ]

        call_ids: set[str] = set()
        result_ids: set[str] = set()
        for u in updates:
            if u.contents:
                for c in u.contents:
                    if getattr(c, "type", None) == "function_call":
                        if c.call_id:
                            call_ids.add(c.call_id)
                    elif getattr(c, "type", None) == "function_result":
                        if c.call_id:
                            result_ids.add(c.call_id)

        assert call_ids == result_ids
        assert len(call_ids) == 1


class TestMockChatClientClassAttributes:
    """Tests for MockChatClient class attributes."""

    def test_otel_provider_name(self) -> None:
        """OTEL_PROVIDER_NAME is set to 'mock'."""
        assert MockChatClient.OTEL_PROVIDER_NAME == "mock"

    def test_mock_prefix_constant(self) -> None:
        """MOCK_PREFIX is set correctly."""
        assert MockChatClient.MOCK_PREFIX == MOCK_PREFIX

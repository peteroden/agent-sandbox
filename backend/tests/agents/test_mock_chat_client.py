"""Tests for MockChatClient.

Tests the BaseChatClient implementation with @use_function_invocation.
Phase 1: tool pattern -> FunctionCallContent.
Phase 2: decorator calls back with tool results -> text output.
"""

from collections.abc import MutableSequence
from typing import Any
from unittest.mock import MagicMock

import pytest
from agent_framework import ChatMessage, ChatResponse, ChatResponseUpdate, Content, Role

from agent_sandbox.agents.mock_chat_client import MockChatClient

# === Constants ===
MOCK_PREFIX = "[Mock] "
TEST_MESSAGE = "hello world"
TOOL_ADD = "add_numbers"
TOOL_ECHO = "echo_text"
CALL_ID = "call_test123"


def _msgs(text: str) -> MutableSequence[ChatMessage]:
    return [ChatMessage(role=Role.USER, text=text)]


def _tool_result_msgs(
    user_text: str, call_id: str, tool: str,
    args: dict[str, Any], result: Any,
) -> MutableSequence[ChatMessage]:
    """Simulate framework callback: user + assistant/function_call + tool/result."""
    return [
        ChatMessage(role=Role.USER, text=user_text),
        ChatMessage(role=Role.ASSISTANT, contents=[
            Content.from_function_call(
                call_id=call_id, name=tool, arguments=args),
        ]),
        ChatMessage(role=Role.TOOL, contents=[
            Content.from_function_result(call_id=call_id, result=result),
        ]),
    ]


def _opts() -> dict[str, Any]:
    return {}


@pytest.fixture
def mock_tool_provider() -> MagicMock:
    """Provider with add_numbers(a, b) and echo_text(text)."""
    tool = MagicMock()
    add_fn = MagicMock()
    add_fn.name = TOOL_ADD
    add_fn.parameters = MagicMock(return_value={
        "type": "object",
        "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
        "required": ["a", "b"],
    })
    echo_fn = MagicMock()
    echo_fn.name = TOOL_ECHO
    echo_fn.parameters = MagicMock(return_value={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    })
    tool.functions = [add_fn, echo_fn]
    return tool


# ── Response basics ──────────────────────────────────────────────────

class TestResponse:
    @pytest.mark.asyncio
    async def test_returns_chat_response(self) -> None:
        r = await MockChatClient()._inner_get_response(messages=_msgs(TEST_MESSAGE), options=_opts())
        assert isinstance(r, ChatResponse)

    @pytest.mark.asyncio
    async def test_echoes_with_prefix(self) -> None:
        r = await MockChatClient()._inner_get_response(messages=_msgs(TEST_MESSAGE), options=_opts())
        text = r.text or (r.messages[0].text if r.messages else "")
        assert text.startswith(MOCK_PREFIX) and TEST_MESSAGE in text

    @pytest.mark.asyncio
    async def test_streaming_yields_updates(self) -> None:
        updates = [u async for u in MockChatClient()._inner_get_streaming_response(
            messages=_msgs(TEST_MESSAGE), options=_opts())]
        assert all(isinstance(u, ChatResponseUpdate) for u in updates)
        assert TEST_MESSAGE in "".join(u.text or "" for u in updates)

    @pytest.mark.asyncio
    async def test_empty_messages(self) -> None:
        r = await MockChatClient()._inner_get_response(messages=[], options=_opts())
        assert isinstance(r, ChatResponse)


# ── Phase 1: tool detection → FunctionCallContent ────────────────────

class TestToolDetection:
    @pytest.mark.parametrize(("msg", "tool", "args"), [
        (f"use {TOOL_ADD} 5 3", TOOL_ADD, {"a": 5, "b": 3}),
        (f"use {TOOL_ECHO} hello", TOOL_ECHO, {"text": "hello"}),
        ("no tool here", None, None),
    ], ids=["add", "echo", "none"])
    @pytest.mark.asyncio
    async def test_detection(
        self, mock_tool_provider: MagicMock,
        msg: str, tool: str | None, args: dict[str, Any] | None,
    ) -> None:
        updates = [u async for u in MockChatClient(tools=[mock_tool_provider])
                   ._inner_get_streaming_response(messages=_msgs(msg), options=_opts())]
        fcs = [c for u in updates for c in u.contents if c.type == "function_call"]
        if tool is None:
            assert len(fcs) == 0
        else:
            assert len(fcs) == 1
            assert fcs[0].name == tool
            parsed = fcs[0].parse_arguments()
            assert all(parsed[k] == v for k, v in args.items())

    @pytest.mark.asyncio
    async def test_no_function_result_emitted(self, mock_tool_provider: MagicMock) -> None:
        """Phase 1 emits only function_call, never function_result."""
        updates = [u async for u in MockChatClient(tools=[mock_tool_provider])
                   ._inner_get_streaming_response(messages=_msgs(f"use {TOOL_ADD} 5 3"), options=_opts())]
        frs = [c for u in updates for c in u.contents if c.type == "function_result"]
        assert len(frs) == 0


# ── Phase 2: tool-result callback → text output ─────────────────────

class TestToolResultCallback:
    @pytest.mark.asyncio
    async def test_string_result(self, mock_tool_provider: MagicMock) -> None:
        msgs = _tool_result_msgs(f"use {TOOL_ADD} 5 3", CALL_ID, TOOL_ADD, {
                                 "a": 5, "b": 3}, "8")
        updates = [u async for u in MockChatClient(tools=[mock_tool_provider])
                   ._inner_get_streaming_response(messages=msgs, options=_opts())]
        assert "8" in "".join(u.text or "" for u in updates)

    @pytest.mark.asyncio
    async def test_mcp_list_result(self, mock_tool_provider: MagicMock) -> None:
        """MCP-style [{"type":"text","text":"8"}] is extracted as '8'."""
        mcp_result = [{"type": "text", "text": "8"}]
        msgs = _tool_result_msgs(f"use {TOOL_ADD} 5 3", CALL_ID, TOOL_ADD, {
                                 "a": 5, "b": 3}, mcp_result)
        updates = [u async for u in MockChatClient(tools=[mock_tool_provider])
                   ._inner_get_streaming_response(messages=msgs, options=_opts())]
        text = "".join(u.text or "" for u in updates)
        assert "8" in text
        assert isinstance(text, str)

    @pytest.mark.asyncio
    async def test_content_object_result(self, mock_tool_provider: MagicMock) -> None:
        """Framework Content objects in result are extracted correctly."""
        content_result = [Content.from_text(text="8")]
        msgs = _tool_result_msgs(f"use {TOOL_ADD} 5 3", CALL_ID, TOOL_ADD, {
                                 "a": 5, "b": 3}, content_result)
        updates = [u async for u in MockChatClient(tools=[mock_tool_provider])
                   ._inner_get_streaming_response(messages=msgs, options=_opts())]
        text = "".join(u.text or "" for u in updates)
        assert text == "8"

    @pytest.mark.asyncio
    async def test_no_extra_function_call(self, mock_tool_provider: MagicMock) -> None:
        msgs = _tool_result_msgs(f"use {TOOL_ADD} 5 3", CALL_ID, TOOL_ADD, {
                                 "a": 5, "b": 3}, "8")
        updates = [u async for u in MockChatClient(tools=[mock_tool_provider])
                   ._inner_get_streaming_response(messages=msgs, options=_opts())]
        fcs = [c for u in updates for c in u.contents if c.type == "function_call"]
        assert len(fcs) == 0


# ── Class attributes ─────────────────────────────────────────────────

class TestAttributes:
    def test_otel_provider(self) -> None:
        assert MockChatClient.OTEL_PROVIDER_NAME == "mock"

    def test_prefix(self) -> None:
        assert MockChatClient.MOCK_PREFIX == MOCK_PREFIX

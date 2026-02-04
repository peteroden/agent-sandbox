"""Tests for MockAgent."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from agent_framework import ChatMessage
from agent_framework._types import AgentResponseUpdate

from agent_sandbox.agents.mock_agent import MockAgent

# === Local Constants ===
AGENT_NAME = "MockAgent"
AGENT_PREFIX = "[Mock] "
TOOL_NAME_ECHO = "echo"
TOOL_NAME_ADD = "add"
TOOL_NAME_SUBTRACT = "subtract"
TOOL_DESC_ECHO = "Echo a message back"
TOOL_PARAM_MESSAGE = "message"


async def get_stream_text(agent: MockAgent, message: str) -> str:
    """Collect all text from run_stream updates."""
    updates = [update async for update in agent.run_stream(message)]
    return "".join(str(u.text) for u in updates if u.text)


@pytest.fixture
def mock_agent() -> MockAgent:
    """Create a MockAgent instance for testing."""
    return MockAgent()


class TestMockAgentRunStream:
    """Tests for MockAgent.run_stream() method."""

    @pytest.mark.asyncio
    async def test_run_stream_yields_updates(self, mock_agent: MockAgent) -> None:
        """run_stream() should yield AgentResponseUpdate objects."""
        updates = [update async for update in mock_agent.run_stream("Hello")]

        assert len(updates) >= 1
        assert all(isinstance(u, AgentResponseUpdate) for u in updates)

    @pytest.mark.asyncio
    async def test_run_stream_contains_echo(self, mock_agent: MockAgent) -> None:
        """run_stream() should include echoed content."""
        updates = [update async for update in mock_agent.run_stream("Hello")]

        # Combine all text from updates
        all_text = "".join(str(u.text) for u in updates if u.text)
        assert f"{AGENT_PREFIX}Echo: Hello" in all_text

    @pytest.mark.asyncio
    async def test_run_stream_handles_none_messages(self, mock_agent: MockAgent) -> None:
        """run_stream() should handle None messages gracefully."""
        text = await get_stream_text(mock_agent, "")

        assert "No message" in text or "Echo:" in text

    @pytest.mark.asyncio
    async def test_run_stream_extracts_last_user_message(
        self, mock_agent: MockAgent
    ) -> None:
        """run_stream() should echo the last user message from a sequence."""
        messages = [
            ChatMessage(role="user", text="First"),
            ChatMessage(role="assistant", text="Response"),
            ChatMessage(role="user", text="Second"),
        ]
        updates = [update async for update in mock_agent.run_stream(messages)]
        all_text = "".join(str(u.text) for u in updates if u.text)

        assert "Second" in all_text
        assert "First" not in all_text


class TestMockAgentDefaults:
    """Tests for MockAgent default values."""

    def test_default_name(self) -> None:
        """Default name should be MockAgent."""
        agent = MockAgent()
        assert agent.name == AGENT_NAME

    def test_default_response_prefix(self) -> None:
        """Default response prefix should be [Mock]."""
        agent = MockAgent()
        assert agent.response_prefix == AGENT_PREFIX

    def test_custom_name(self) -> None:
        """Should accept custom name."""
        custom_name = "CustomAgent"
        agent = MockAgent(name=custom_name)
        assert agent.name == custom_name

    def test_custom_prefix(self) -> None:
        """Should accept custom prefix."""
        custom_prefix = "[Test] "
        agent = MockAgent(response_prefix=custom_prefix)
        assert agent.response_prefix == custom_prefix


class TestMockAgentToolSupport:
    """Tests for MockAgent tool support."""

    @pytest.fixture
    def mock_mcp_tool(self) -> MagicMock:
        """Create a mock MCP tool provider (like MCPStreamableHTTPTool)."""
        tool = MagicMock()
        # Mock the functions property to return available tools
        mock_func = MagicMock()
        mock_func.name = TOOL_NAME_ECHO
        mock_func.description = TOOL_DESC_ECHO
        # Add parameter schema for schema-based arg building
        mock_func.parameters = MagicMock(return_value={
            "type": "object",
            "properties": {TOOL_PARAM_MESSAGE: {"type": "string"}},
            "required": [TOOL_PARAM_MESSAGE],
        })
        tool.functions = [mock_func]
        # Mock call_tool to return a result
        tool.call_tool = AsyncMock(return_value="Echo: hello world")
        return tool

    @pytest.fixture
    def dict_tool(self) -> dict[str, Any]:
        """Create a dict-based tool info for simple testing."""
        return {
            "name": "test_tool",
            "description": "A test tool",
        }

    def test_mock_agent_accepts_tools(self, mock_mcp_tool: MagicMock) -> None:
        """MockAgent constructor accepts tools list."""
        agent = MockAgent(tools=[mock_mcp_tool])

        assert len(agent.tools) == 1

    def test_mock_agent_discovers_tools_from_mcp_tool(
        self, mock_mcp_tool: MagicMock
    ) -> None:
        """MockAgent discovers tools from MCPStreamableHTTPTool.functions."""
        agent = MockAgent(tools=[mock_mcp_tool])

        available = agent._get_available_tools()
        assert len(available) == 1
        assert available[0][0] == TOOL_NAME_ECHO

    def test_mock_agent_discovers_tools_from_dict(
        self, dict_tool: dict[str, Any]
    ) -> None:
        """MockAgent discovers tools from dict-based tool info."""
        agent = MockAgent(tools=[dict_tool])

        available = agent._get_available_tools()
        assert len(available) == 1
        assert available[0][0] == "test_tool"

    @pytest.mark.asyncio
    async def test_mock_agent_detects_tool_request(
        self, mock_mcp_tool: MagicMock
    ) -> None:
        """MockAgent identifies 'use echo' in message."""
        agent = MockAgent(tools=[mock_mcp_tool])

        updates = [update async for update in agent.run_stream(f"use {TOOL_NAME_ECHO} hello world")]

        # Tool should be called
        mock_mcp_tool.call_tool.assert_called_once()
        assert len(updates) >= 1

    @pytest.mark.asyncio
    async def test_mock_agent_executes_tool_with_args(
        self, mock_mcp_tool: MagicMock
    ) -> None:
        """MockAgent calls tool with message argument."""
        agent = MockAgent(tools=[mock_mcp_tool])

        updates = [update async for update in agent.run_stream(f"use {TOOL_NAME_ECHO} test message")]

        mock_mcp_tool.call_tool.assert_called_once_with(
            TOOL_NAME_ECHO, message="test message")
        assert len(updates) >= 1

    @pytest.mark.asyncio
    async def test_mock_agent_returns_tool_result(
        self, mock_mcp_tool: MagicMock
    ) -> None:
        """Response includes tool output in function_result content."""
        mock_mcp_tool.call_tool.return_value = "Echo: hello world"
        agent = MockAgent(tools=[mock_mcp_tool])

        updates = [update async for update in agent.run_stream(f"use {TOOL_NAME_ECHO} hello world")]

        # Tool results are emitted as Content.from_function_result
        results = [
            c.result
            for u in updates
            if u.contents
            for c in u.contents
            if getattr(c, "type", None) == "function_result"
        ]
        assert any("Echo: hello world" in r for r in results)

    @pytest.mark.asyncio
    async def test_mock_agent_tool_stream(
        self, mock_mcp_tool: MagicMock
    ) -> None:
        """run_stream() includes tool output in function_result content."""
        mock_mcp_tool.call_tool.return_value = "Echo: streamed"
        agent = MockAgent(tools=[mock_mcp_tool])

        updates = [update async for update in agent.run_stream(f"use {TOOL_NAME_ECHO} streamed")]

        # Tool results are emitted as Content.from_function_result
        results = [
            c.result
            for u in updates
            if u.contents
            for c in u.contents
            if getattr(c, "type", None) == "function_result"
        ]
        assert any("Echo: streamed" in r for r in results)

    @pytest.mark.asyncio
    async def test_mock_agent_no_tool_match_normal_response(
        self, mock_mcp_tool: MagicMock
    ) -> None:
        """Normal echo response when no tool matched."""
        agent = MockAgent(tools=[mock_mcp_tool])

        updates = [update async for update in agent.run_stream("just say hello")]

        # Tool should not be called
        mock_mcp_tool.call_tool.assert_not_called()
        all_text = "".join(str(u.text) for u in updates if u.text)
        assert f"{AGENT_PREFIX}Echo:" in all_text

    @pytest.mark.asyncio
    async def test_mock_agent_handles_content_list_result(
        self, mock_mcp_tool: MagicMock
    ) -> None:
        """MockAgent extracts text from Content objects in result."""
        # Simulate Content objects returned by MCPStreamableHTTPTool
        mock_content = MagicMock()
        mock_content.text = "Extracted text"
        mock_mcp_tool.call_tool.return_value = [mock_content]
        agent = MockAgent(tools=[mock_mcp_tool])

        updates = [update async for update in agent.run_stream(f"use {TOOL_NAME_ECHO} test")]

        # Tool results are emitted as Content.from_function_result
        results = [
            c.result
            for u in updates
            if u.contents
            for c in u.contents
            if getattr(c, "type", None) == "function_result"
        ]
        assert any("Extracted text" in r for r in results)


class TestMockAgentNumberTools:
    """Tests for MockAgent number tool support (add, subtract)."""

    @pytest.fixture
    def mock_number_tool(self) -> MagicMock:
        """Create a mock MCP tool provider for number operations."""
        tool = MagicMock()
        # Mock the functions property for add and subtract with schemas
        add_func = MagicMock()
        add_func.name = TOOL_NAME_ADD
        add_func.parameters = MagicMock(return_value={
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
            "required": ["a", "b"],
        })
        subtract_func = MagicMock()
        subtract_func.name = TOOL_NAME_SUBTRACT
        subtract_func.parameters = MagicMock(return_value={
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
            "required": ["a", "b"],
        })
        tool.functions = [add_func, subtract_func]
        # Mock call_tool to return a result
        tool.call_tool = AsyncMock(return_value=8)
        return tool

    def test_parse_numbers_simple(self) -> None:
        """Parse two space-separated numbers."""
        agent = MockAgent()
        result = agent._parse_numbers("5 3")

        assert result == [5, 3]

    def test_parse_numbers_with_commas(self) -> None:
        """Parse comma-separated numbers."""
        agent = MockAgent()
        result = agent._parse_numbers("5, 3")

        assert result == [5, 3]

    def test_parse_numbers_negative(self) -> None:
        """Parse negative numbers."""
        agent = MockAgent()
        result = agent._parse_numbers("-5 3")

        assert result == [-5, 3]

    def test_parse_numbers_with_text(self) -> None:
        """Parse numbers embedded in text."""
        agent = MockAgent()
        result = agent._parse_numbers("add 10 and 20 together")

        assert result == [10, 20]

    def test_parse_numbers_single_number(self) -> None:
        """Return single-element list for one number."""
        agent = MockAgent()
        result = agent._parse_numbers("5")

        assert result == [5]

    def test_parse_numbers_no_numbers(self) -> None:
        """Return empty list if no numbers found."""
        agent = MockAgent()
        result = agent._parse_numbers("hello world")

        assert result == []

    @pytest.mark.asyncio
    async def test_mock_agent_executes_add_tool(
        self, mock_number_tool: MagicMock
    ) -> None:
        """MockAgent calls add tool with a, b arguments."""
        mock_number_tool.call_tool.return_value = 8
        agent = MockAgent(tools=[mock_number_tool])

        updates = [update async for update in agent.run_stream(f"use {TOOL_NAME_ADD} 5 3")]

        mock_number_tool.call_tool.assert_called_once_with(
            TOOL_NAME_ADD, a=5, b=3)
        assert len(updates) >= 1

    @pytest.mark.asyncio
    async def test_mock_agent_returns_add_result(
        self, mock_number_tool: MagicMock
    ) -> None:
        """Response includes add tool result in function_result content."""
        mock_number_tool.call_tool.return_value = 8
        agent = MockAgent(tools=[mock_number_tool])

        updates = [update async for update in agent.run_stream(f"use {TOOL_NAME_ADD} 5 3")]

        # Tool results are emitted as Content.from_function_result
        results = [
            c.result
            for u in updates
            if u.contents
            for c in u.contents
            if getattr(c, "type", None) == "function_result"
        ]
        assert any("8" in r for r in results)

    @pytest.mark.asyncio
    async def test_mock_agent_executes_subtract_tool(
        self, mock_number_tool: MagicMock
    ) -> None:
        """MockAgent calls subtract tool with a, b arguments."""
        mock_number_tool.call_tool.return_value = 7
        agent = MockAgent(tools=[mock_number_tool])

        updates = [update async for update in agent.run_stream(f"use {TOOL_NAME_SUBTRACT} 10 3")]

        mock_number_tool.call_tool.assert_called_once_with(
            TOOL_NAME_SUBTRACT, a=10, b=3)
        assert len(updates) >= 1

    @pytest.mark.asyncio
    async def test_mock_agent_handles_negative_number_args(
        self, mock_number_tool: MagicMock
    ) -> None:
        """MockAgent handles negative numbers in tool args."""
        mock_number_tool.call_tool.return_value = -2
        agent = MockAgent(tools=[mock_number_tool])

        updates = [update async for update in agent.run_stream(f"use {TOOL_NAME_ADD} -5 3")]

        mock_number_tool.call_tool.assert_called_once_with(
            TOOL_NAME_ADD, a=-5, b=3)
        assert len(updates) >= 1

    @pytest.mark.asyncio
    async def test_mock_agent_returns_error_for_single_number_arg(
        self, mock_number_tool: MagicMock
    ) -> None:
        """MockAgent returns helpful error when only one number provided."""
        agent = MockAgent(tools=[mock_number_tool])

        updates = [update async for update in agent.run_stream(f"use {TOOL_NAME_ADD} 54")]

        all_text = "".join(str(u.text) for u in updates if u.text)
        assert "requires two numbers" in all_text or "Error" in all_text
        mock_number_tool.call_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_stream_emits_function_call_content(
        self, mock_number_tool: MagicMock
    ) -> None:
        """run_stream() emits Content.from_function_call for tool calls."""
        mock_number_tool.call_tool.return_value = 8
        agent = MockAgent(tools=[mock_number_tool])

        updates = [update async for update in agent.run_stream(f"use {TOOL_NAME_ADD} 5 3")]

        # Find update with function_call content
        function_calls = [
            u
            for u in updates
            if u.contents
            and any(getattr(c, "type", None) == "function_call" for c in u.contents)
        ]
        assert len(function_calls) >= 1
        fc = function_calls[0].contents[0]
        assert fc.name == TOOL_NAME_ADD
        assert fc.call_id is not None

    @pytest.mark.asyncio
    async def test_run_stream_emits_function_result_content(
        self, mock_number_tool: MagicMock
    ) -> None:
        """run_stream() emits Content.from_function_result after tool execution."""
        mock_number_tool.call_tool.return_value = 8
        agent = MockAgent(tools=[mock_number_tool])

        updates = [update async for update in agent.run_stream(f"use {TOOL_NAME_ADD} 5 3")]

        # Find update with function_result content
        function_results = [
            u
            for u in updates
            if u.contents
            and any(getattr(c, "type", None) == "function_result" for c in u.contents)
        ]
        assert len(function_results) >= 1
        fr = function_results[0].contents[0]
        assert "8" in fr.result

    @pytest.mark.asyncio
    async def test_run_stream_call_id_matches_between_call_and_result(
        self, mock_number_tool: MagicMock
    ) -> None:
        """call_id matches between function_call and function_result."""
        mock_number_tool.call_tool.return_value = 8
        agent = MockAgent(tools=[mock_number_tool])

        updates = [update async for update in agent.run_stream(f"use {TOOL_NAME_ADD} 5 3")]

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

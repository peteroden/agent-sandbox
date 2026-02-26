"""Tests for the MCP gateway server."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp import types
from mcp.shared.exceptions import McpError

from agent_sandbox.mcp_gateway import (
    _build_resource_index,
    _build_tool_index,
    create_gateway_server,
)

AGENT_TOOL_NAME = "AGUIAssistant"
SUB_TOOL_NAME = "system_stats"
SUB_TOOL_DESC = "Get system statistics"
SUB_TOOL_SCHEMA: dict[str, Any] = {"type": "object", "properties": {}}
SERVER_NAME = "demo-app"


def _make_function(
    name: str = SUB_TOOL_NAME, description: str = SUB_TOOL_DESC
) -> MagicMock:
    """Create a mock FunctionTool."""
    func = MagicMock()
    func.name = name
    func.description = description
    func.input_model = SUB_TOOL_SCHEMA
    return func


def _make_mcp_tool(
    server_name: str = SERVER_NAME,
    functions: list[MagicMock] | None = None,
    connected: bool = True,
) -> MagicMock:
    """Create a mock MCPStreamableHTTPTool."""
    tool = MagicMock()
    tool.name = f"{server_name}-tools"
    tool.functions = functions or [_make_function()]
    tool.session = AsyncMock() if connected else None
    return tool


def _make_agent() -> MagicMock:
    """Create a mock Agent with as_tool()."""
    agent = MagicMock()
    agent_tool = MagicMock()
    agent_tool.name = AGENT_TOOL_NAME
    agent_tool.description = "Agent assistant"
    agent_tool.parameters.return_value = {
        "type": "object",
        "properties": {"message": {"type": "string"}},
    }
    agent_tool.input_model = None
    agent_tool.invoke = AsyncMock(return_value="Agent response")
    agent._get_agent_name.return_value = AGENT_TOOL_NAME
    agent.as_tool.return_value = agent_tool
    return agent


async def _call_list_tools(server: Any) -> list[types.Tool]:
    """Invoke the server's list_tools handler."""
    handler = server.request_handlers[types.ListToolsRequest]
    req = types.ListToolsRequest(method="tools/list")
    result = await handler(req)
    return result.root.tools


async def _call_tool(
    server: Any, name: str, arguments: dict[str, Any] | None = None
) -> Any:
    """Invoke the server's call_tool handler."""
    handler = server.request_handlers[types.CallToolRequest]
    req = types.CallToolRequest(
        method="tools/call",
        params=types.CallToolRequestParams(
            name=name, arguments=arguments or {}
        ),
    )
    result = await handler(req)
    return result.root


async def _read_resource(server: Any, uri: str) -> Any:
    """Invoke the server's read_resource handler."""
    handler = server.request_handlers[types.ReadResourceRequest]
    req = types.ReadResourceRequest(
        method="resources/read",
        params=types.ReadResourceRequestParams(uri=uri),
    )
    result = await handler(req)
    return result.root


class TestBuildToolIndex:
    """Tests for _build_tool_index."""

    def test_maps_function_names_to_tools(self) -> None:
        func_a = _make_function("tool_a")
        func_b = _make_function("tool_b")
        mcp_tool = _make_mcp_tool(functions=[func_a, func_b])

        index = _build_tool_index([mcp_tool])

        assert "tool_a" in index
        assert "tool_b" in index
        assert index["tool_a"] is mcp_tool

    def test_empty_tools_list(self) -> None:
        assert _build_tool_index([]) == {}

    def test_multiple_servers(self) -> None:
        tool_a = _make_mcp_tool("server-a", [_make_function("func_a")])
        tool_b = _make_mcp_tool("server-b", [_make_function("func_b")])

        index = _build_tool_index([tool_a, tool_b])

        assert index["func_a"] is tool_a
        assert index["func_b"] is tool_b


class TestBuildResourceIndex:
    """Tests for _build_resource_index."""

    def test_maps_server_name_to_tool(self) -> None:
        mcp_tool = _make_mcp_tool("demo-app")
        index = _build_resource_index([mcp_tool])
        assert "demo-app" in index

    def test_strips_tools_suffix(self) -> None:
        mcp_tool = _make_mcp_tool("text")
        index = _build_resource_index([mcp_tool])
        assert "text" in index


class TestListTools:
    """Tests for the gateway list_tools handler."""

    @pytest.mark.asyncio()
    async def test_lists_agent_and_sub_tools(self) -> None:
        agent = _make_agent()
        mcp_tools = [
            _make_mcp_tool("demo-app", [_make_function("system_stats")]),
            _make_mcp_tool("text", [_make_function("echo_text")]),
        ]
        gateway = create_gateway_server(agent, mcp_tools)

        tools = await _call_list_tools(gateway)
        tool_names = [t.name for t in tools]

        assert AGENT_TOOL_NAME in tool_names
        assert "system_stats" in tool_names
        assert "echo_text" in tool_names
        assert len(tool_names) == 3

    @pytest.mark.asyncio()
    async def test_agent_only_when_no_mcp_tools(self) -> None:
        agent = _make_agent()
        gateway = create_gateway_server(agent, [])

        tools = await _call_list_tools(gateway)

        assert len(tools) == 1
        assert tools[0].name == AGENT_TOOL_NAME


class TestCallTool:
    """Tests for the gateway call_tool handler."""

    @pytest.mark.asyncio()
    async def test_routes_to_agent(self) -> None:
        agent = _make_agent()
        gateway = create_gateway_server(agent, [])

        result = await _call_tool(gateway, AGENT_TOOL_NAME, {"message": "hello"})

        assert len(result.content) == 1
        assert result.content[0].text == "Agent response"

    @pytest.mark.asyncio()
    async def test_routes_to_sub_server(self) -> None:
        agent = _make_agent()
        mcp_tool = _make_mcp_tool()
        mcp_tool.session.call_tool.return_value = MagicMock(
            content=[types.TextContent(type="text", text='{"cpu": 50}')]
        )
        gateway = create_gateway_server(agent, [mcp_tool])

        result = await _call_tool(gateway, SUB_TOOL_NAME, {})

        mcp_tool.session.call_tool.assert_awaited_once_with(
            SUB_TOOL_NAME, arguments={}
        )
        assert len(result.content) == 1
        assert result.content[0].text == '{"cpu": 50}'

    @pytest.mark.asyncio()
    async def test_unknown_tool_returns_error(self) -> None:
        agent = _make_agent()
        gateway = create_gateway_server(agent, [])

        result = await _call_tool(gateway, "nonexistent")

        assert result.isError is True
        assert "not found" in result.content[0].text

    @pytest.mark.asyncio()
    async def test_disconnected_sub_server_returns_error(self) -> None:
        agent = _make_agent()
        mcp_tool = _make_mcp_tool(connected=False)
        gateway = create_gateway_server(agent, [mcp_tool])

        result = await _call_tool(gateway, SUB_TOOL_NAME)

        assert result.isError is True
        assert "not found" in result.content[0].text


class TestReadResource:
    """Tests for the gateway read_resource handler."""

    @pytest.mark.asyncio()
    async def test_proxies_ui_resource(self) -> None:
        agent = _make_agent()
        mcp_tool = _make_mcp_tool()
        expected_contents = [
            types.TextResourceContents(
                uri="ui://demo-app/view.html",
                text="<html></html>",
                mimeType="text/html",
            )
        ]
        mcp_tool.session.read_resource.return_value = MagicMock(
            contents=expected_contents
        )
        gateway = create_gateway_server(agent, [mcp_tool])

        result = await _read_resource(gateway, "ui://demo-app/view.html")

        mcp_tool.session.read_resource.assert_awaited_once_with(
            uri="ui://demo-app/view.html"
        )

    @pytest.mark.asyncio()
    async def test_rejects_non_ui_scheme(self) -> None:
        agent = _make_agent()
        gateway = create_gateway_server(agent, [])

        with pytest.raises(McpError, match="Unsupported URI scheme"):
            await _read_resource(gateway, "https://example.com")

    @pytest.mark.asyncio()
    async def test_unknown_server_raises_error(self) -> None:
        agent = _make_agent()
        gateway = create_gateway_server(agent, [])

        with pytest.raises(McpError, match="not connected"):
            await _read_resource(gateway, "ui://unknown/view.html")

"""MCP Gateway server that aggregates sub-server tools alongside the agent.

Implements the MCP Gateway pattern: a single MCP endpoint that exposes
all sub-server tools for direct invocation, plus the AGUIAssistant agent
tool for LLM-orchestrated interactions. Routes tools/call requests to
the correct sub-server session based on tool name.
"""

import logging
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlparse

from agent_framework import Agent, MCPStreamableHTTPTool
from mcp import types
from mcp.server import Server
from mcp.shared.exceptions import McpError
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def _build_tool_index(
    mcp_tools: list[MCPStreamableHTTPTool],
) -> dict[str, MCPStreamableHTTPTool]:
    """Map each function name to its owning MCPStreamableHTTPTool."""
    index: dict[str, MCPStreamableHTTPTool] = {}
    for tool in mcp_tools:
        for func in tool.functions:
            index[func.name] = tool
    return index


def _build_resource_index(
    mcp_tools: list[MCPStreamableHTTPTool],
) -> dict[str, MCPStreamableHTTPTool]:
    """Map server names (from ui:// hostnames) to MCPStreamableHTTPTool."""
    index: dict[str, MCPStreamableHTTPTool] = {}
    for tool in mcp_tools:
        # name format: "{server_name}-tools"
        server_name = tool.name.removesuffix("-tools")
        index[server_name] = tool
    return index


def create_gateway_server(
    agent: Agent,
    mcp_tools: list[MCPStreamableHTTPTool] | None = None,
    *,
    server_name: str = "agent-sandbox",
    version: str | None = None,
) -> Server[Any]:
    """Create an MCP gateway server aggregating agent and sub-server tools.

    Args:
        agent: The Agent instance (exposed as AGUIAssistant tool).
        mcp_tools: Connected MCPStreamableHTTPTool instances from sub-servers.
        server_name: Name for the MCP server.
        version: Server version string.

    Returns:
        An MCP Server with all tools registered.
    """
    server: Server[Any] = Server(name=server_name, version=version)  # type: ignore[call-arg]

    agent_tool = agent.as_tool(name=agent._get_agent_name())
    tools = mcp_tools or []
    tool_index = _build_tool_index(tools)
    resource_index = _build_resource_index(tools)

    @server.list_tools()  # type: ignore
    async def _list_tools() -> list[types.Tool]:
        """List agent tool plus all sub-server tools."""
        result: list[types.Tool] = []

        # Agent tool
        result.append(
            types.Tool(
                name=agent_tool.name,
                description=agent_tool.description,
                inputSchema=agent_tool.parameters(),
            )
        )

        # Sub-server tools
        for mcp_tool in tools:
            for func in mcp_tool.functions:
                schema = func.input_model if isinstance(func.input_model, dict) else {}
                # Ensure schema has required "type": "object" per MCP spec
                if "type" not in schema:
                    schema = {**schema, "type": "object"}
                result.append(
                    types.Tool(
                        name=func.name,
                        description=func.description or "",
                        inputSchema=schema,  # type: ignore[arg-type]
                    )
                )

        return result

    @server.call_tool()  # type: ignore
    async def _call_tool(
        name: str, arguments: dict[str, Any]
    ) -> Sequence[
        types.TextContent
        | types.ImageContent
        | types.AudioContent
        | types.EmbeddedResource
    ]:
        """Route tool calls to agent or sub-server."""
        # Agent tool
        if name == agent_tool.name:
            try:
                args_instance: BaseModel | dict[str, Any] = (
                    agent_tool.input_model(**arguments)
                    if agent_tool.input_model is not None
                    else arguments
                )
                result = await agent_tool.invoke(arguments=args_instance)
            except Exception as e:
                raise McpError(
                    error=types.ErrorData(
                        code=types.INTERNAL_ERROR,
                        message=f"Error calling agent: {e}",
                    ),
                ) from e

            if isinstance(result, str):
                return [types.TextContent(type="text", text=result)]
            return [types.TextContent(type="text", text=str(result))]

        # Sub-server tool
        mcp_tool = tool_index.get(name)
        if not mcp_tool or not mcp_tool.session:
            raise McpError(
                error=types.ErrorData(
                    code=types.INTERNAL_ERROR,
                    message=f"Tool {name} not found",
                ),
            )

        try:
            result = await mcp_tool.session.call_tool(name, arguments=arguments)
            return list(result.content) if result.content else []
        except McpError:
            raise
        except Exception as e:
            raise McpError(
                error=types.ErrorData(
                    code=types.INTERNAL_ERROR,
                    message=f"Error calling tool {name}: {e}",
                ),
            ) from e

    @server.list_resources()  # type: ignore
    async def _list_resources() -> list[types.Resource]:
        """List resources from all sub-servers."""
        resources: list[types.Resource] = []
        for mcp_tool in tools:
            if not mcp_tool.session:
                continue
            try:
                result = await mcp_tool.session.list_resources()
                resources.extend(result.resources)
            except Exception as e:
                logger.warning("Failed to list resources from %s: %s", mcp_tool.name, e)
        return resources

    @server.read_resource()  # type: ignore
    async def _read_resource(uri: Any) -> Any:
        """Proxy resource reads to the correct sub-server."""
        uri_str = str(uri)
        parsed = urlparse(uri_str)
        if parsed.scheme != "ui":
            raise McpError(
                error=types.ErrorData(
                    code=types.INVALID_PARAMS,
                    message=f"Unsupported URI scheme: {parsed.scheme}",
                ),
            )

        server_key = parsed.netloc
        mcp_tool = resource_index.get(server_key)
        if not mcp_tool or not mcp_tool.session:
            raise McpError(
                error=types.ErrorData(
                    code=types.INTERNAL_ERROR,
                    message=f"MCP server not connected: {server_key}",
                ),
            )

        return await mcp_tool.session.read_resource(uri=uri_str)

    return server

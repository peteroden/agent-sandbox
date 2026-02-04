"""TracingMCPTool with OpenTelemetry context propagation.

This module provides an MCP tool wrapper that propagates trace context
via the _meta field for proper distributed tracing across MCP boundaries.
"""

from typing import Any

from agent_framework import MCPStreamableHTTPTool

from agent_sandbox.otel_utils import inject_otel_context_to_meta


class TracingMCPTool(MCPStreamableHTTPTool):
    """MCPStreamableHTTPTool subclass that propagates trace context via _meta.

    HTTP headers don't work for MCP trace propagation because the MCP library
    spawns internal async tasks that break OpenTelemetry context. Instead, we
    inject trace context into the _meta field which is passed through the MCP
    JSON-RPC protocol.

    Based on: https://github.com/timvw/fastmcp-otel-langfuse
    """

    async def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Override call_tool to inject trace context via _meta field."""
        # Inject current trace context into _meta
        meta = inject_otel_context_to_meta()
        if meta:
            kwargs["_meta"] = meta

        return await super().call_tool(tool_name, **kwargs)

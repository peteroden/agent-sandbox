"""TracingTool wrapper for automatic trace context injection."""

from typing import Any

from ._inject import inject

try:
    from agent_framework import MCPStreamableHTTPTool

    class TracingTool(MCPStreamableHTTPTool):
        """MCPStreamableHTTPTool that auto-injects trace context via _meta.

        This is required for distributed tracing because HTTPX instrumentation
        does not work with the agent-framework's async task spawning pattern.

        The trace context is captured at call_tool() invocation (where context
        is still valid) and injected into the _meta field, which is passed
        through the MCP JSON-RPC protocol.

        Example:
            tool = TracingTool(url="http://localhost:8001/mcp")
            result = await tool.call_tool("my_tool", arg="value")
            # _meta is automatically injected with traceparent
        """

        async def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
            """Override call_tool to inject trace context via _meta field."""
            kwargs["_meta"] = inject()
            return await super().call_tool(tool_name, **kwargs)

except ImportError:
    # agent-framework not installed
    TracingTool = None  # type: ignore[misc,assignment]

"""MCP Trace Context - W3C Trace Context propagation for MCP tool calls.

This package provides utilities for propagating trace context across MCP
tool boundaries via the _meta field convention.

Usage:
    # Server side - extract context from _meta
    from mcp_trace_context import propagate

    @mcp.tool()
    @propagate
    def my_tool(arg: str, _meta=None) -> str:
        return f"Result: {arg}"

    # Client side - inject context into _meta
    from mcp_trace_context import inject

    meta = inject()
    await tool.call_tool("my_tool", arg="test", _meta=meta)

    # Or use TracingTool for automatic injection
    from mcp_trace_context import TracingTool

    tool = TracingTool(url="http://localhost:8001/mcp")
    await tool.call_tool("my_tool", arg="test")
"""

from ._extract import extract
from ._inject import inject
from ._propagate import propagate

__all__ = ["inject", "extract", "propagate"]

# Optional: TracingTool if agent-framework is installed
try:
    from ._tool import TracingTool

    if TracingTool is not None:
        __all__.append("TracingTool")
except ImportError:
    TracingTool = None  # type: ignore[misc,assignment]

"""TracingMCPTool with OpenTelemetry context propagation.

This module provides an MCP tool wrapper that propagates trace context
via the _meta field for proper distributed tracing across MCP boundaries.

Why _meta instead of HTTP headers?
The agent-framework spawns internal async tasks that break OpenTelemetry
context before HTTP requests are made. This means HTTPX instrumentation
cannot propagate trace context to MCP tool calls - it creates orphan traces.

The solution is to capture trace context at the call_tool() invocation point
(where context is still valid) and inject it into the _meta field, which is
passed through the MCP JSON-RPC protocol. MCP servers then extract this
context using @with_otel_context_from_meta decorator.

Based on: https://github.com/timvw/fastmcp-otel-langfuse
"""

import logging
from typing import Any

from agent_framework import MCPStreamableHTTPTool
from opentelemetry import trace

from agent_sandbox.otel_utils import inject_otel_context_to_meta

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("agent_sandbox.tools")


class TracingMCPTool(MCPStreamableHTTPTool):
    """MCPStreamableHTTPTool subclass that propagates trace context via _meta.

    This is required for distributed tracing because HTTPX instrumentation
    does not work with the agent-framework's async task spawning pattern.
    """

    async def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Override call_tool to inject trace context via _meta field."""
        with tracer.start_as_current_span(
            "mcp_tool.call",
            attributes={
                "tool.name": tool_name,
                "mcp.url": self.url,
            },
        ) as span:
            # Inject current trace context into _meta
            meta = inject_otel_context_to_meta()
            if meta:
                kwargs["_meta"] = meta

            logger.info("Calling MCP tool '%s'", tool_name)
            try:
                result = await super().call_tool(tool_name, **kwargs)
                span.set_attribute("tool.success", True)
                logger.info("MCP tool '%s' completed successfully", tool_name)
                return result
            except Exception as e:
                span.set_attribute("tool.success", False)
                span.set_attribute("error", str(e))
                span.record_exception(e)
                logger.exception("MCP tool '%s' failed", tool_name)
                raise

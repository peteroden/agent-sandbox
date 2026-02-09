"""MCP server for text processing tools."""

import logging
import os
from typing import Any

from agent_framework.observability import configure_otel_providers, get_tracer
from mcp_trace_context import propagate

# Configure OpenTelemetry BEFORE FastMCP creates its internal Starlette app
configure_otel_providers()

from fastmcp import FastMCP  # noqa: E402 - must be after instrumentation
from starlette.requests import Request  # noqa: E402
from starlette.responses import JSONResponse, Response  # noqa: E402

# Set up logging
logger = logging.getLogger(__name__)
tracer = get_tracer()

# Create MCP server instance
mcp = FastMCP(
    name="Text Tools",
    instructions=(
        "MCP server providing tools for text such as "
        "echoing messages or uppercasing text."
    ),
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> Response:
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


@mcp.tool()
@propagate
def echo_text(message: str, _meta: dict[str, Any] | None = None) -> str:
    """TEXT TOOL: Echoes a text message back to the user.

    DO NOT USE for math operations. Use ONLY for echoing/repeating/saying text.

    Input: A text string message
    Output: The message prefixed with 'Echo: '

    Examples:
    - "echo hello" -> echo_text(message="hello") -> "Echo: hello"
    - "repeat goodbye" -> echo_text(message="goodbye") -> "Echo: goodbye"
    - "say hi there" -> echo_text(message="hi there") -> "Echo: hi there"

    Args:
        message: The text message to echo back.
        _meta: Optional MCP metadata containing trace context (internal use).

    Returns:
        The message prefixed with 'Echo: '.
    """
    logger.info("Echoing message: %s", message)
    # Nested span to verify trace context propagation is working
    with tracer.start_as_current_span("tool.echo_text.process") as process_span:
        result = f"Echo: {message}"
        logger.info("Echo result: %s", result)
        process_span.set_attribute("result", result)
    return result


if __name__ == "__main__":
    port = int(os.environ.get("MCP_TEXT_PORT", "8001"))
    mcp.run(transport="streamable-http", port=port)

"""MCP server for number processing tools."""

import logging
import os
from typing import Any

# Configure telemetry BEFORE FastMCP creates its internal Starlette app
# This ensures StarletteInstrumentor patches the class before instantiation
from agent_sandbox.telemetry import configure_mcp_telemetry, get_tracer, instrument_mcp_app
from agent_sandbox.otel_utils import with_otel_context_from_meta

configure_mcp_telemetry("numbers-mcp")
instrument_mcp_app()  # Global instrumentation - patches Starlette class
tracer = get_tracer()
logger = logging.getLogger(__name__)

from fastmcp import FastMCP  # noqa: E402 - must be after instrumentation
from starlette.requests import Request  # noqa: E402
from starlette.responses import JSONResponse, Response  # noqa: E402

# Create MCP server instance
mcp = FastMCP(
    name="Number Tools",
    instructions=(
        "MCP server providing tools for number operations "
        "such as addition and subtraction."
    ),
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> Response:
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


@mcp.tool()
@with_otel_context_from_meta
def add_numbers(a: int, b: int, _meta: dict[str, Any] | None = None) -> int:
    """MATH TOOL: Adds two integers and returns their sum.

    DO NOT USE for text operations. Use ONLY for addition/sum/plus/total.

    Input: Two integers a and b
    Output: Integer result of a + b

    Examples:
    - "what is 10 plus 20" -> add_numbers(a=10, b=20) -> 30
    - "sum of 1 and 2" -> add_numbers(a=1, b=2) -> 3

    Args:
        a: First integer to add.
        b: Second integer to add.
        _meta: Optional MCP metadata containing trace context (internal use).

    Returns:
        The sum of a and b.
    """
    with tracer.start_as_current_span("tool.add_numbers", attributes={"a": a, "b": b}) as span:
        logger.info("Adding numbers: %d + %d", a, b)
        result = a + b
        logger.info("Addition result: %d", result)
        span.set_attribute("result", result)
        return result


@mcp.tool()
@with_otel_context_from_meta
def subtract_numbers(a: int, b: int, _meta: dict[str, Any] | None = None) -> int:
    """MATH TOOL: Subtracts second integer from first and returns the difference.

    DO NOT USE for text operations. Use ONLY for subtraction/minus/difference.

    Input: Two integers a and b
    Output: Integer result of a - b

    Examples:
    - "subtract 3 from 10" -> subtract_numbers(a=10, b=3) -> 7
    - "what is 20 minus 5" -> subtract_numbers(a=20, b=5) -> 15
    - "difference between 8 and 3" -> subtract_numbers(a=8, b=3) -> 5

    Args:
        a: Integer to subtract from.
        b: Integer to subtract.
        _meta: Optional MCP metadata containing trace context (internal use).

    Returns:
        The difference (a - b).
    """
    with tracer.start_as_current_span("tool.subtract_numbers", attributes={"a": a, "b": b}) as span:
        logger.info("Subtracting numbers: %d - %d", a, b)
        result = a - b
        logger.info("Subtraction result: %d", result)
        span.set_attribute("result", result)
        return result


if __name__ == "__main__":
    port = int(os.environ.get("MCP_NUMBERS_PORT", "8002"))
    mcp.run(transport="streamable-http", port=port)

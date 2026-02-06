# MCP Trace Context

W3C Trace Context propagation for MCP tool calls via the `_meta` field.

## Why This Package?

When using Microsoft Agent Framework with MCP servers, trace context is lost because:

1. Agent Framework spawns async tasks for tool calls
2. OpenTelemetry's contextvar-based propagation breaks across task boundaries
3. HTTPX instrumentation cannot inject headers since context is already gone

This package solves the problem by:

- **Client side**: Injecting `traceparent` into the MCP `_meta` field before the async boundary
- **Server side**: Extracting `traceparent` from `_meta` and restoring the trace context

## Installation

```bash
pip install mcp-trace-context

# With TracingTool support
pip install mcp-trace-context[agent-framework]
```

## Usage

### Server Side (MCP Tool)

```python
from fastmcp import FastMCP
from mcp_trace_context import propagate

mcp = FastMCP("my-server")

@mcp.tool()
@propagate  # Extracts trace context from _meta
def my_tool(arg: str) -> str:
    return f"Result: {arg}"
```

### Client Side (Tool Caller)

```python
from mcp_trace_context import TracingTool

# TracingTool auto-injects _meta on every call
tool = TracingTool(url="http://localhost:8001/mcp")
result = await tool.call_tool("my_tool", arg="value")
```

Or manual injection:

```python
from mcp_trace_context import inject

meta = inject()  # {"traceparent": "00-...", "tracestate": "..."}
await client.call_tool("my_tool", arg="value", _meta=meta)
```

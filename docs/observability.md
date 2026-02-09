# Observability Guide

This guide explains how to add logging, tracing, and metrics to the Agent Sandbox backend and MCP servers.

## Overview

The Agent Sandbox uses OpenTelemetry for distributed tracing across:

- **Frontend** (`agent-sandbox-frontend`) - Browser spans via fetch instrumentation
- **Server** (`agent-sandbox-server`) - FastAPI/Starlette HTTP spans via Agent Framework
- **MCP Servers** (`text-mcp`, `numbers-mcp`) - Tool execution spans

Traces flow: `Frontend → Server → MCP Server → Tool`

## Quick Start

### Environment Variables

```bash
# Enable Agent Framework instrumentation
export ENABLE_INSTRUMENTATION=true

# OTLP protocol (http/protobuf for SigNoz HTTP endpoint)
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

# Signal-specific OTLP endpoints (HTTP exporters need full paths)
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4318/v1/traces
export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://localhost:4318/v1/logs
export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://localhost:4318/v1/metrics

# Service name for telemetry attribution
export OTEL_SERVICE_NAME=agent-sandbox-server
```

### Using dev.sh

```bash
# Start with SigNoz (includes OTLP collector)
./scripts/dev.sh --signoz --azure

# View traces at http://localhost:8080
```

## Instrumenting an MCP Server

### 1. Configure Telemetry Before Imports

Telemetry must be configured **before** creating the FastMCP instance. This ensures Starlette instrumentation patches the class before instantiation.

```python
"""my_mcp_server.py"""
import logging
from typing import Any

from agent_framework.observability import configure_otel_providers, get_tracer
from mcp_trace_context import propagate

# Step 1: Configure telemetry FIRST (before FastMCP import)
configure_otel_providers()

# Step 2: Now import FastMCP (after instrumentation)
from fastmcp import FastMCP  # noqa: E402

# Set up logging and tracing
logger = logging.getLogger(__name__)
tracer = get_tracer()

mcp = FastMCP(name="My Tools")
```

### 2. Decorate Tools for Trace Context

Use `@propagate` from `mcp_trace_context` to receive trace context from the calling agent:

```python
@mcp.tool()
@propagate
def my_tool(arg: str, _meta: dict[str, Any] | None = None) -> str:
    """My tool description.
    
    Args:
        arg: The input argument.
        _meta: MCP metadata containing trace context (internal use).
    
    Returns:
        The result.
    """
    logger.info("Processing arg: %s", arg)
    with tracer.start_as_current_span("tool.my_tool.process") as span:
        result = process(arg)
        span.set_attribute("result", result)
        return result
```

**Key points:**

1. `@propagate` extracts `traceparent` from `_meta` and activates it
2. `_meta: dict[str, Any] | None = None` receives the trace context (hidden from users)
3. `tracer.start_as_current_span()` creates a span linked to the parent trace
4. Use standard `logging` - logs are automatically correlated with traces

### 3. Why _meta Instead of HTTP Headers?

The agent-framework spawns async tasks that break OpenTelemetry context before HTTP requests are made. HTTPX instrumentation cannot propagate trace context through MCP calls - it creates orphan traces.

The solution:

1. `TracingTool` captures context at `call_tool()` and injects it into `_meta`
2. `@propagate` extracts and activates this context on the server
3. Tool spans are correctly linked to the parent trace

## Instrumenting the Main Server

The main server (`server.py`) uses Agent Framework's built-in observability.

### 1. Configure Telemetry

```python
from agent_framework.observability import configure_otel_providers, get_tracer

# Configure before app creation - reads from environment variables
configure_otel_providers()

logger = logging.getLogger(__name__)
tracer = get_tracer()
```

### 2. Use TracingTool for MCP Connections

When connecting to MCP servers, use `TracingTool` from `mcp_trace_context`:

```python
from mcp_trace_context import TracingTool

tool = TracingTool(
    name="my-mcp-tools",
    url="http://localhost:8001/mcp",
    description="Tools from my MCP server",
)
await tool.connect()
```

### 3. Instrument Starlette for HTTP Spans

```python
from opentelemetry.instrumentation.starlette import StarletteInstrumentor

# After app creation
if os.environ.get("ENABLE_INSTRUMENTATION", "").lower() == "true":
    StarletteInstrumentor.instrument_app(app)
```

## Creating Custom Spans

### Basic Span

```python
from agent_framework.observability import get_tracer

tracer = get_tracer()

with tracer.start_as_current_span("my_operation") as span:
    span.set_attribute("key", "value")
    result = do_work()
    span.set_attribute("result_size", len(result))
```

### Nested Spans

```python
with tracer.start_as_current_span("parent_operation") as parent:
    # Child span is automatically linked to parent
    with tracer.start_as_current_span("child_operation") as child:
        child.set_attribute("step", "processing")
        result = process()
```

### Adding Events

```python
with tracer.start_as_current_span("operation") as span:
    span.add_event("Starting processing", {"item_count": 100})
    process_items()
    span.add_event("Processing complete")
```

### Recording Exceptions

```python
from opentelemetry import trace

with tracer.start_as_current_span("operation") as span:
    try:
        risky_operation()
    except Exception as e:
        span.record_exception(e)
        span.set_status(trace.StatusCode.ERROR, str(e))
        raise
```

## Logging

Python logs are automatically correlated with traces when using Agent Framework observability:

```python
import logging

logger = logging.getLogger(__name__)

def my_function():
    logger.info("Processing started: item_id=%d", 123)
    # Log appears in SigNoz with trace context attached
```

## Module Reference

### Agent Framework Observability

```python
from agent_framework.observability import configure_otel_providers, get_tracer

# Configure providers (call once at startup)
configure_otel_providers()

# Get a tracer for creating spans
tracer = get_tracer()
```

### mcp-trace-context Package

```python
from mcp_trace_context import inject, extract, propagate, TracingTool
```

#### `@propagate`

Decorator that extracts trace context from `_meta` parameter and activates it.

```python
@propagate
def my_tool(arg: str, _meta: dict | None = None) -> str:
    # Trace context is now active
    pass
```

#### `inject() -> dict`

Captures current trace context for injection into `_meta`.

```python
from mcp_trace_context import inject

meta = inject()
# Returns {"traceparent": "00-...", "tracestate": "..."}
```

#### `extract(meta: dict | None) -> Context`

Extracts OpenTelemetry context from `_meta` dictionary.

```python
from mcp_trace_context import extract

ctx = extract(meta)
```

#### `TracingTool`

MCP tool wrapper that auto-injects trace context via `_meta`.

```python
from mcp_trace_context import TracingTool

tool = TracingTool(url="http://localhost:8001/mcp")
await tool.connect()
# All call_tool() invocations automatically include trace context
```

## Viewing Traces

### SigNoz (Recommended)

1. Start with `./scripts/dev.sh --signoz`
2. Open http://localhost:8080
3. Navigate to Traces → Search by service or trace ID

### Trace ID from Frontend

The frontend logs trace IDs in console. Search for traces using:

- Browser DevTools console: look for `traceparent` header
- SigNoz: paste trace ID in search

## Troubleshooting

### Traces Not Appearing

1. Verify `ENABLE_INSTRUMENTATION=true` is set
2. Check that signal-specific endpoints include full paths (`/v1/traces`)
3. Verify `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf` for HTTP endpoints

### Traces Not Connecting (Frontend → Backend)

1. Verify Starlette instrumentation is enabled
2. Check CORS allows `traceparent` header
3. Ensure `StarletteInstrumentor.instrument_app(app)` is called

### Traces Not Connecting (Backend → MCP)

1. Ensure `@propagate` decorator is applied to tools
2. Verify `_meta` parameter is in tool signature
3. Confirm `TracingTool` is used (not `MCPStreamableHTTPTool`)

### Orphan Traces from MCP Servers

This is expected for:

- SSE streaming connections (GET /mcp)
- Health checks
- MCP initialization requests

Tool execution traces should be properly linked via `_meta`.

### Console Output for Debugging

```bash
export ENABLE_CONSOLE_EXPORTERS=true
```

This prints spans to console for immediate visibility without needing SigNoz.

# Plan: Align mcp-trace-context with SEP-414, SEP-2028, and agent-framework PR #3780

> **Status**: Obsolete — Superseded by `remove-mcp-trace-context.md`
> **Created**: 2026-02-10
> **Context**: This plan can be implemented in a clean context with no prior conversation needed.
>
> **Note**: The `mcp-trace-context` package has been removed. Built-in tracing support in `agent-framework>=1.0.0rc1` and `fastmcp>=3.0.1` replaces all functionality described here.

## Background

Three upstream changes converge on how OpenTelemetry trace context propagates across MCP boundaries:

| Change | What it does | Status |
|---|---|---|
| [agent-framework PR #3780](https://github.com/microsoft/agent-framework/pull/3780) | Adds `_inject_otel_into_mcp_meta()` to inject OTel context into `params._meta` via `session.call_tool(..., meta=)` | Approved, merging |
| [MCP spec SEP-414](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/414) | Documents `traceparent`, `tracestate`, `baggage` as reserved keys in `params._meta` (exception to DNS prefix rule) | Accepted by core maintainers |
| [MCP spec SEP-2028](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2028) | Auto-forwards W3C trace context from `_meta` to downstream HTTP headers | In review (proposal) |

Our `mcp-trace-context` package (`backend/packages/mcp-trace-context/`) provides client-side injection (`TracingTool`) and server-side extraction (`@propagate`) for this exact pattern. This plan aligns it with the spec and upstream code, and makes swapping to official SDK implementations free.

## Current state

### Package structure

```
backend/packages/mcp-trace-context/
├── pyproject.toml                    # v1.0.0, depends on opentelemetry-api>=1.20.0
├── src/mcp_trace_context/
│   ├── __init__.py                   # Exports: inject, extract, propagate, TracingTool (conditional)
│   ├── _inject.py                    # inject() -> dict[str, str]
│   ├── _extract.py                   # extract(meta) -> Context
│   ├── _propagate.py                 # @propagate decorator
│   └── _tool.py                      # TracingTool(MCPStreamableHTTPTool)
└── tests/
    ├── test_inject.py
    ├── test_extract.py
    ├── test_propagate.py
    └── test_tool.py
```

### Installed SDK versions (as of 2026-02-10)

| Package | Version | Native OTel injection/extraction? |
|---|---|---|
| `mcp` | 1.26.0 | No — but `session.call_tool()` has `meta: dict[str, Any] \| None` param that maps to `params._meta` |
| `fastmcp` | 2.14.4 | No |
| `agent-framework` | 1.0.0b260130 | No — PR #3780 adds it |

### Key finding: `params._meta` vs `arguments._meta`

The MCP SDK's `session.call_tool(name, arguments, meta=)` puts `meta` into `params._meta` in the JSON-RPC request. Our `TracingTool` currently does `kwargs["_meta"] = inject()`, which puts trace context inside `arguments` — **the wrong location per SEP-414**.

SEP-414 specifies:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_weather",
    "arguments": { "location": "New York" },
    "_meta": { "traceparent": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01" }
  }
}
```

### Key finding: `extract()` hardcodes W3C fields

`extract()` manually copies `traceparent`/`tracestate`/`baggage` by name before passing to `otel_extract()`. PR #3780 is explicitly "propagator-agnostic — forwards whatever keys the configured propagator(s) produce". Our `inject()` is already propagator-agnostic (delegates to `otel_inject()`), but `extract()` is not.

## Changes

### Phase 1: Align `inject()` with agent-framework's `_inject_otel_into_mcp_meta()`

**File**: `backend/packages/mcp-trace-context/src/mcp_trace_context/_inject.py`

PR #3780 adds this exact function:

```python
def _inject_otel_into_mcp_meta(meta: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Inject OpenTelemetry trace context into MCP request _meta via the global propagator(s)."""
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    if not carrier:
        return meta

    if meta is None:
        meta = {}
    for key, value in carrier.items():
        if key not in meta:
            meta[key] = value

    return meta
```

Our `inject()` should mirror this:

1. Change signature to `inject(meta: dict[str, Any] | None = None) -> dict[str, Any]`
2. Implement merge-not-clobber loop: iterate carrier keys, only set those not already present in `meta`
3. Remove explicit `context=context.get_current()` parameter from `otel_inject` call — let OTel use the implicit current context (matches PR #3780's convention)
4. Return `{}` instead of `None` when no active span (our existing empty dict return is fine — but note PR #3780 returns `None`; we keep `{}` for backward compatibility since callers already pass our return value to `meta=`)

**Tests** (`test_inject.py`):

- **Merge-not-clobber**: Call `inject(meta={"progressToken": "abc"})` inside an active span. Assert `traceparent` is added AND `progressToken` is preserved.
- **No-clobber**: Call `inject(meta={"traceparent": "existing"})` inside an active span. Assert the existing `traceparent` value is NOT overwritten.
- **Backward compat**: Call `inject()` with no args — still returns `dict` with `traceparent` when inside a span.
- Existing tests must continue passing.

### Phase 2: Make `extract()` propagator-agnostic

**File**: `backend/packages/mcp-trace-context/src/mcp_trace_context/_extract.py`

Current code manually filters for W3C fields:

```python
carrier: dict[str, str] = {}
if "traceparent" in meta:
    carrier["traceparent"] = str(meta["traceparent"])
if "tracestate" in meta:
    carrier["tracestate"] = str(meta["tracestate"])
if "baggage" in meta:
    carrier["baggage"] = str(meta["baggage"])
if carrier:
    return otel_extract(carrier)
```

Replace with:

```python
if not meta:
    return context.get_current()
return otel_extract(meta)
```

Pass the entire `meta` dict directly to `otel_extract()`. OTel's `TextMapPropagator` will extract only the fields it understands. This ensures B3, Jaeger, and custom propagators work without code changes.

**Tests** (`test_extract.py`):

- Existing tests continue passing (they use W3C fields, which still work).
- **Extra keys ignored**: Call `extract({"traceparent": "00-...", "progressToken": "abc"})`. Assert context is extracted correctly (OTel ignores unknown keys).
- **Empty fields**: Call `extract({"unrelated": "value"})`. Assert returns current context (no trace context fields present).

### Phase 3: Fix `TracingTool` to use `params._meta` (not `arguments._meta`)

**File**: `backend/packages/mcp-trace-context/src/mcp_trace_context/_tool.py`

Current code (wrong placement):

```python
async def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
    kwargs["_meta"] = inject()
    return await super().call_tool(tool_name, **kwargs)
```

This puts trace context inside `arguments`. The MCP SDK's `session.call_tool(name, arguments=, meta=)` has a separate `meta` parameter that maps to `params._meta`.

The challenge: `MCPStreamableHTTPTool.call_tool()` (from agent-framework) does NOT currently expose the `meta` parameter. It calls `self.session.call_tool(tool_name, arguments=filtered_kwargs)` without forwarding `meta`.

**Approach**: Override `call_tool()` to replicate the parent's logic but add `meta=inject()` to the `session.call_tool()` call. This mirrors exactly what PR #3780 does to `MCPTool.call_tool()`.

```python
async def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
    """Override call_tool to inject trace context via params._meta."""
    # Filter out non-tool kwargs (same as parent)
    filtered_kwargs = {
        k: v for k, v in kwargs.items()
        if k not in {"chat_options", "tools", "tool_choice", "thread",
                     "conversation_id", "options", "response_format"}
    }

    otel_meta = inject()

    for attempt in range(2):
        try:
            result = await self.session.call_tool(
                tool_name,
                arguments=filtered_kwargs,
                meta=otel_meta if otel_meta else None,
            )
            return result
        except Exception:
            if attempt == 0:
                await self.connect()
            else:
                raise
```

> **Note**: If the parent class internals are too complex to replicate cleanly, an alternative approach is to monkeypatch `self.session.call_tool` to inject `meta` transparently. The exact approach should be decided during implementation based on the parent class's actual behavior.

**Tests** (`test_tool.py`):

- **`meta=` parameter test**: Mock `session.call_tool` and assert it was called with `meta=` keyword containing trace fields (NOT with `_meta` inside `arguments`). This mirrors PR #3780's test at lines 2765–2773.
- **Propagator-agnostic assertion**: Assert `meta` is a dict with length > 0 when a span is active, without checking specific header names. This matches PR #3780's test pattern.
- Existing tests updated to reflect the new call path.

### Phase 4: Verify `@propagate` works with `params._meta` path

**File**: `backend/packages/mcp-trace-context/src/mcp_trace_context/_propagate.py`

After Phase 3, trace context arrives in `params._meta` instead of `arguments._meta`. FastMCP (v2.14.4) dispatches tool calls by extracting `params._meta` and may or may not forward it to tool function kwargs.

**Investigation needed during implementation**:

1. Start a FastMCP server, call a tool with `meta={"traceparent": "00-..."}` via `session.call_tool()`, and check whether `_meta` arrives as a kwarg in the tool function.
2. If **yes**: `@propagate` works as-is. No changes needed.
3. If **no**: Add a FastMCP/Starlette middleware or lifespan hook that intercepts incoming JSON-RPC requests, reads `params._meta`, and attaches trace context to the OTel context before tool dispatch. The `@propagate` decorator then becomes optional (kept for backward compat but the middleware handles the real work). This mirrors [Python SDK instrumentation PR #1693](https://github.com/modelcontextprotocol/python-sdk/pull/1693).

**If middleware approach is needed**, create `backend/packages/mcp-trace-context/src/mcp_trace_context/_middleware.py`:

```python
def add_trace_context_middleware(app):
    """Add middleware that extracts trace context from MCP params._meta."""
    # Intercept incoming JSON-RPC, extract _meta, attach OTel context
    ...
```

**Tests**: If middleware is needed, test that an incoming JSON-RPC `tools/call` with `params._meta.traceparent` results in the correct trace context being active inside the tool function.

### Phase 5: Passthrough detection for zero-change swapout

**File**: `backend/packages/mcp-trace-context/src/mcp_trace_context/_compat.py` (new)

Add detection utilities:

```python
def upstream_injects() -> bool:
    """Check if agent-framework natively injects trace context into _meta."""
    try:
        from agent_framework._mcp import _inject_otel_into_mcp_meta
        return True
    except ImportError:
        return False

def upstream_extracts() -> bool:
    """Check if the MCP Python SDK natively extracts trace context from _meta."""
    # Future: check for mcp or fastmcp native extraction
    return False
```

**File**: `backend/packages/mcp-trace-context/src/mcp_trace_context/_tool.py`

When `upstream_injects()` returns `True`, `TracingTool.call_tool()` delegates to `super()` without its own injection:

```python
async def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
    if upstream_injects():
        return await super().call_tool(tool_name, **kwargs)
    # ... existing injection logic ...
```

Log at `DEBUG` level when passthrough is active.

**File**: `backend/packages/mcp-trace-context/src/mcp_trace_context/_propagate.py`

When `upstream_extracts()` returns `True`, `@propagate` returns the original function unwrapped:

```python
def propagate(func=None, *, param="_meta", force=False):
    if func is not None and not force and upstream_extracts():
        return func  # no-op — upstream handles extraction
    # ... existing wrapping logic ...
```

The `force=True` escape hatch allows explicit control during migration testing.

**Tests** (`test_compat.py`):

- **Passthrough injection**: Mock `agent_framework._mcp._inject_otel_into_mcp_meta` as importable. Assert `TracingTool.call_tool()` delegates without its own injection.
- **Passthrough extraction**: Mock upstream extraction as available. Assert `@propagate` returns the original function object (identity).
- **Force override**: Assert `@propagate(force=True)` still wraps even when upstream extraction is available.

### Phase 6: Update integration code

1. **`backend/src/agent_sandbox/registry/mcp_registry.py`**: No import changes needed — `TracingTool` continues to work but now correctly uses `params._meta` and auto-detects upstream support.

2. **`backend/src/agent_sandbox/number_mcp_server.py`** and **`backend/src/agent_sandbox/text_mcp_server.py`**: No changes needed — `@propagate` continues to work but is now propagator-agnostic and auto-detects upstream support.

3. **`backend/src/agent_sandbox/otel_utils.py`**: Delete this file. Grep confirms no production code imports it. It was the predecessor to the `mcp-trace-context` package.

### Phase 7: Version bump and documentation

1. Bump version to `2.0.0` in `backend/packages/mcp-trace-context/pyproject.toml` (breaking: `inject()` signature change, `TracingTool` call path change).

2. Update `backend/packages/mcp-trace-context/README.md` with:
   - Migration notes for the `inject()` signature change
   - Explanation of automatic passthrough when upstream adds native support
   - Reference to SEP-414 and the non-normative JSON-RPC example

## Verification

```bash
# All package tests pass
cd backend && uv run pytest packages/mcp-trace-context/tests/ -v

# All integration tests pass
cd backend && uv run pytest tests/ -v

# Manual: start backend, call a tool, verify traces link in SigNoz/Jaeger
LLM_PROVIDER=mock ./scripts/dev.sh

# Manual: inspect JSON-RPC traffic to confirm traceparent is in params._meta
# (not inside params.arguments)
```

## Key decisions

| Decision | Rationale |
|---|---|
| Mirror PR #3780's merge-not-clobber `if key not in meta` loop | Preserves existing `_meta` keys like `progressToken` per MCP spec |
| Fix `arguments._meta` → `params._meta` placement | SEP-414 spec requires trace context in `params._meta`, not tool arguments |
| Make `extract()` propagator-agnostic by passing full `meta` to `otel_extract()` | Matches PR #3780's stated "propagator-agnostic" design; supports B3, Jaeger, etc. |
| Detect-then-passthrough over hard removal | Upgrading agent-framework or MCP SDK is enough — zero `mcp-trace-context` code changes needed |
| `force=True` escape hatch on `@propagate` | Allows explicit control during SDK version transitions |
| Version `2.0.0` (semver major) | `inject()` signature and `TracingTool` call path are breaking changes |

## References

- [SEP-414 spec wording](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/414/files#diff-b562e63d9fb1f6bbb6ddf2807a7f4e9558662e454b33076540a053ae55e46fc0) — adds `traceparent`/`tracestate`/`baggage` as reserved `_meta` keys, with non-normative JSON-RPC example
- [SEP-2028](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2028) — auto-forwarding `_meta` trace fields to HTTP headers with group-based policy
- [agent-framework PR #3780](https://github.com/microsoft/agent-framework/pull/3780) — `_inject_otel_into_mcp_meta()` helper, wired into `MCPTool.call_tool()`, propagator-agnostic
- [OTel semantic conventions for MCP](https://opentelemetry.io/docs/specs/semconv/gen-ai/mcp/#context-propagation) — specifies `_meta` as the carrier for W3C Trace Context keys
- [MCP Python SDK `session.call_tool` signature](https://github.com/modelcontextprotocol/python-sdk) — `meta: dict[str, Any] | None` parameter maps to `params._meta` via `RequestParams.Meta` with `extra="allow"`
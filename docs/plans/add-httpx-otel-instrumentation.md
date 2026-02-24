# Plan: Add httpx OpenTelemetry Instrumentation

> **Status**: Ready
> **Created**: 2026-02-24
> **Context**: Execute in a clean context. Each phase is self-contained with explicit file
> paths and exact code changes.

## Background

The backend has three layers of observability:

| Layer | What | How |
| --- | --- | --- |
| Inbound HTTP | Starlette/FastAPI requests | `StarletteInstrumentor.instrument_app(app)` |
| LLM calls | Azure OpenAI chat completions | `ChatTelemetryLayer` mixin in `AzureOpenAIChatClient` (agent-framework built-in) |
| Outbound HTTP | httpx calls to MCP servers, health checks | **Not instrumented** |

This plan fills the third gap by adding `opentelemetry-instrumentation-httpx` to trace all
outbound HTTP calls. Two production modules use httpx today:

* `backend/src/agent_sandbox/health.py` — sync `httpx.get()` for health checks
* `backend/src/agent_sandbox/registry/mcp_registry.py` — async `httpx.AsyncClient` for MCP
  server health probes

### Why not OpenLLMetry / opentelemetry-instrumentation-openai?

The `agent-framework` package includes `ChatTelemetryLayer`, which already produces full
`gen_ai.*` semantic convention spans (operation name, model, provider, token usage, agent
name/ID, conversation ID). Adding `opentelemetry-instrumentation-openai` on top would create
duplicate spans for every LLM call with no additional value, since all OpenAI SDK usage goes
through `AzureOpenAIChatClient`.

### Design decisions

* **Global monkey-patch** — `HTTPXClientInstrumentor().instrument()` patches both
  `httpx.Client` and `httpx.AsyncClient` at the module level. One call covers all current and
  future httpx usage. No per-file changes needed.
* **Same activation guard** — gated by `ENABLE_INSTRUMENTATION=true`, consistent with the
  existing `StarletteInstrumentor` pattern.
* **Single initialization site** — `server.py` is the only file that needs the instrumentor
  call. MCP sub-servers (`text_mcp_server.py`, `number_mcp_server.py`) make no outbound httpx
  requests.

## Phases

### Phase 0: Add Dependency

> **Agent**: backend-expert
> **Depends on**: Nothing

1. Run `cd backend && uv add opentelemetry-instrumentation-httpx`.
   * Expected resolved version: `0.60b1` (matches existing
     `opentelemetry-instrumentation-starlette==0.60b1` and `opentelemetry-api==1.39.1`).
2. Verify `backend/pyproject.toml` now contains `"opentelemetry-instrumentation-httpx"` in the
   `dependencies` list.
3. Run `cd backend && uv sync` to install.

### Phase 1: Write Failing Test (Red)

> **Agent**: backend-expert
> **Depends on**: Phase 0

Add a test to `backend/tests/test_e2e_tracing.py` verifying that `HTTPXClientInstrumentor`
becomes active when instrumentation is enabled. Follow the existing
`TestMcpTelemetryPropagation` pattern (same file, same `clean_modules` autouse fixture).

Add the following test class after the existing `TestMcpTelemetryPropagation` class:

```python
class TestHttpxInstrumentation:
    """Tests for httpx outbound call instrumentation."""

    def test_httpx_instrumentor_active_when_enabled(self) -> None:
        """HTTPXClientInstrumentor is active when ENABLE_INSTRUMENTATION=true."""
        with patch.dict(os.environ, {"ENABLE_INSTRUMENTATION": "true"}):
            import importlib

            import agent_sandbox.server

            importlib.reload(agent_sandbox.server)

            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

            instrumentor = HTTPXClientInstrumentor()
            assert instrumentor.is_instrumented_by_opentelemetry

            instrumentor.uninstrument()

    def test_httpx_instrumentor_inactive_when_disabled(self) -> None:
        """HTTPXClientInstrumentor is not active when ENABLE_INSTRUMENTATION is unset."""
        with patch.dict(os.environ, {}, clear=True):
            import importlib

            import agent_sandbox.server

            importlib.reload(agent_sandbox.server)

            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

            instrumentor = HTTPXClientInstrumentor()
            assert not instrumentor.is_instrumented_by_opentelemetry
```

Required imports to add at the top of the file (alongside existing imports):

```python
import os
from unittest.mock import patch
```

Run `cd backend && uv run pytest tests/test_e2e_tracing.py -v` and confirm both new tests
**fail** (Red phase).

### Phase 2: Implement (Green)

> **Agent**: backend-expert
> **Depends on**: Phase 1

Edit `backend/src/agent_sandbox/server.py`.

**Step 1 — Add import.** Add this import near the existing `StarletteInstrumentor` import
(line 17):

```python
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
```

**Step 2 — Activate instrumentor.** Find the module-level `ENABLE_INSTRUMENTATION` guard
block near line 311 (after CORS middleware setup):

```python
# before:
if os.environ.get("ENABLE_INSTRUMENTATION", "").lower() == "true":
    StarletteInstrumentor.instrument_app(app)
```

Change to:

```python
# after:
if os.environ.get("ENABLE_INSTRUMENTATION", "").lower() == "true":
    StarletteInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
```

Run `cd backend && uv run pytest tests/test_e2e_tracing.py -v` and confirm both new tests
**pass** (Green phase).

### Phase 3: Run Full Test Suite

> **Agent**: backend-expert
> **Depends on**: Phase 2

1. Run `cd backend && uv run pytest -v` — all unit tests pass.
2. Run `cd e2e && pnpm test` — all E2E tests pass (no regressions).

If tests fail, diagnose. Common issues:

* **Import error for `HTTPXClientInstrumentor`** — Phase 0 dependency not installed. Rerun
  `cd backend && uv sync`.
* **Existing httpx mocks break** — unlikely, since test mocks patch at
  `agent_sandbox.health.httpx.get` and `agent_sandbox.registry.mcp_registry.httpx`, which
  work regardless of instrumentation wrapping. If issues arise, ensure
  `HTTPXClientInstrumentor().uninstrument()` is called in test teardown.
* **E2E trace propagation tests fail** — the httpx instrumentor auto-propagates W3C
  `traceparent`/`tracestate` headers on outgoing requests, which should enhance (not break)
  existing trace continuity.

### Phase 4: Code Review

> **Agent**: backend-expert
> **Depends on**: Phase 3

Self-review all changes using `.github/instructions/code-review.instructions.md`:

* [ ] `opentelemetry-instrumentation-httpx` added to `pyproject.toml` dependencies
* [ ] Import added to `server.py`
* [ ] `HTTPXClientInstrumentor().instrument()` called inside `ENABLE_INSTRUMENTATION` guard
* [ ] Two new tests verify instrumentor activation and non-activation
* [ ] No security regressions — no new secrets, no new user input handling
* [ ] No duplicate instrumentation — only httpx HTTP-level spans added
* [ ] Unit tests pass: `cd backend && uv run pytest`
* [ ] E2E tests pass: `cd e2e && pnpm test`

## Files Changed

| File | Change |
| --- | --- |
| `backend/pyproject.toml` | Add `"opentelemetry-instrumentation-httpx"` to dependencies |
| `backend/src/agent_sandbox/server.py` | Add import + `HTTPXClientInstrumentor().instrument()` call |
| `backend/tests/test_e2e_tracing.py` | Add `TestHttpxInstrumentation` test class (2 tests) |

## Files Not Changed

These files use httpx but require no modifications — the global monkey-patch covers them
automatically:

| File | httpx Usage |
| --- | --- |
| `backend/src/agent_sandbox/health.py` | `httpx.get()` (sync) |
| `backend/src/agent_sandbox/registry/mcp_registry.py` | `httpx.AsyncClient` (async) |
| `backend/src/agent_sandbox/text_mcp_server.py` | None |
| `backend/src/agent_sandbox/number_mcp_server.py` | None |

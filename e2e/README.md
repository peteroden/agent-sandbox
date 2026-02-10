# E2E Tests

Playwright end-to-end tests for the Agent Sandbox. These tests verify the full stack (frontend, backend, and MCP servers) using the mock LLM provider for deterministic results.

## Tech Stack

- **Framework**: Playwright Test
- **Browser**: Chromium (via `@playwright/browser-chromium`)
- **Package Manager**: pnpm

## Getting Started

### Install Dependencies

```bash
pnpm install
```

Chromium downloads automatically via the `@playwright/browser-chromium` package.

### Run Tests

```bash
pnpm test          # Run all E2E tests
pnpm test:ui       # Interactive UI mode
pnpm test:debug    # Debug mode with inspector
pnpm test:report   # View last HTML report
```

Tests auto-start the full dev stack via `scripts/dev.sh --mock`. If the stack is already running, Playwright reuses it (set `CI=true` to force a fresh start).

## Project Structure

```text
e2e/
├── tests/                                 # Test specifications
│   ├── chat-echo.spec.ts                  # AG-UI Chat echo_text tool
│   ├── chat-add.spec.ts                   # AG-UI Chat add_numbers tool
│   ├── mcp-chat-echo.spec.ts              # MCP Chat echo_text tool
│   ├── mcp-chat-add.spec.ts               # MCP Chat add_numbers tool
│   ├── trace-propagation.spec.ts          # W3C traceparent consistency
│   └── backend-trace-propagation.spec.ts  # Backend OTLP span verification
├── helpers/                               # Shared test utilities
│   ├── constants.ts                       # Commands, expected values, timeouts
│   ├── trace-interceptor.ts               # Captures traceparent headers
│   ├── agui-response-capture.ts           # Parses AG-UI SSE responses
│   ├── otlp-collector.ts                  # In-memory OTLP HTTP receiver
│   └── wait-for-backend.ts               # Backend health-check polling
├── global-setup.ts                        # Starts OTLP collector
├── global-teardown.ts                     # Stops OTLP collector
├── playwright.config.ts
├── package.json
└── tsconfig.json
```

## Test Coverage

### Functional Tests

Each test sends a tool invocation command (e.g., `use echo_text hello world`) and verifies the correct result appears:

| Test File | Page | Tool | Expected Result |
| --------- | ---- | ---- | --------------- |
| `chat-echo.spec.ts` | `/chat` (AG-UI) | `echo_text` | `Echo: hello world` |
| `chat-add.spec.ts` | `/chat` (AG-UI) | `add_numbers` | `8` |
| `mcp-chat-echo.spec.ts` | `/mcp-chat` | `echo_text` | `Echo: hello world` |
| `mcp-chat-add.spec.ts` | `/mcp-chat` | `add_numbers` | `8` |

### Trace Propagation Tests

`trace-propagation.spec.ts` validates W3C `traceparent` header consistency:

- All requests within a single message share the same traceId
- Different messages produce different traceIds
- Verified for both AG-UI Chat and MCP Chat pages

### Backend OTLP Trace Tests

`backend-trace-propagation.spec.ts` verifies end-to-end trace propagation through the backend:

- An in-memory OTLP collector (port 4319) receives span exports from the backend
- Tests confirm the backend produces OTLP spans containing the same traceId the browser sent
- Verified for both AG-UI Chat and MCP Chat pages

The OTLP collector starts via `global-setup.ts` before the webServer and stops in `global-teardown.ts`. The `playwright.config.ts` passes `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4319/v1/traces` to the dev server so the backend's `BatchSpanProcessor` exports to the collector.

## Helpers

### TraceInterceptor

Attaches to a Playwright `Page` and captures `traceparent` headers from outgoing requests to `/ag-ui` and `/mcp` endpoints. Provides `getTraceIds()` and `getRequests()` for assertions.

### AgUiResponseCapture

Attaches to a Playwright `Page` and parses AG-UI SSE response bodies. Extracts tool call results from the event stream since the `react-ag-ui` library does not always render tool results in the DOM.

### waitForBackend

Polls the backend health endpoint (`/health` on port 8888) until it responds. Used in `test.beforeAll` because Playwright's `webServer` only waits for the frontend port (5173).

## Configuration

Key settings in `playwright.config.ts`:

| Setting | Value | Notes |
| ------- | ----- | ----- |
| `timeout` | 60s | Per-test timeout |
| `expect.timeout` | 15s | Assertion timeout |
| `globalSetup` | `global-setup.ts` | Starts OTLP collector on port 4319 |
| `globalTeardown` | `global-teardown.ts` | Stops OTLP collector |
| `webServer.command` | `scripts/dev.sh --mock` | Auto-starts full stack with OTLP env vars |
| `webServer.timeout` | 120s | Startup timeout |
| `workers` | 1 | Sequential execution (shared server) |
| `retries` | 0 (local), 1 (CI) | Retry on CI only |

## CI Integration

In CI environments (`CI=true`):

- Playwright starts a fresh dev server (no reuse)
- Failed tests retry once
- GitHub reporter format is used
- Traces are captured on first retry for debugging

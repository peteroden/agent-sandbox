# Scripts

Development scripts for Agent Sandbox orchestration.

## Quick Start

```bash
./scripts/dev.sh
```

This starts all local development services in one terminal with colored, labeled output.

## Available Scripts

| Script   | Purpose                                  |
| -------- | ---------------------------------------- |
| `dev.sh` | Start all services for local development |

## dev.sh Usage

```bash
./scripts/dev.sh [OPTIONS]
```

### Options

| Option             | Description                               |
| ------------------ | ----------------------------------------- |
| `--mock`           | Use mock LLM (fastest, no real responses) |
| `--azure`          | Use Azure OpenAI (requires API keys)      |
| `--backend-only`   | Skip frontend service                     |
| `--frontend-only`  | Skip backend services                     |
| `--signoz`         | Start SigNoz for tracing (auto-configured)|
| `--signoz-stop`    | Stop SigNoz containers and exit           |
| `--signoz-creds`   | Show SigNoz login credentials             |
| `--help`, `-h`     | Show help message                         |

### Examples

```bash
# Start with mock LLM (default)
./scripts/dev.sh

# Start with Azure OpenAI
./scripts/dev.sh --azure

# Backend services only
./scripts/dev.sh --backend-only
```

### Environment Variables

| Variable         | Default | Purpose                 |
| ---------------- | ------- | ----------------------- |
| `LLM_PROVIDER`   | `mock`  | LLM backend (mock/azure) |

## Service Architecture

When running `./scripts/dev.sh`, these services start with hot reload enabled:

| Service      | Port  | Color   | Description              |
| ------------ | ----- | ------- | ------------------------ |
| `server`     | 8888  | Blue    | AG-UI server             |
| `mcp:text`   | 8001  | Cyan    | Text MCP server          |
| `mcp:num`    | 8002  | Magenta | Number MCP server        |
| `frontend`   | 5173  | Green   | Vite dev server          |
| `signoz`     | 8080  | -       | SigNoz UI (with --signoz)|
| `otel`       | 4318  | -       | OTLP collector           |

All Python services use uvicorn with `--reload` (WatchFiles) for automatic restart on code changes. The frontend uses Vite's built-in HMR.

## Health Check

Verify all services are running:

```bash
cd backend && uv run python -m agent_sandbox.health
```

This displays a status table showing which services are healthy.

## Observability

For distributed tracing with SigNoz, see [signoz-setup.md](../docs/signoz-setup.md).

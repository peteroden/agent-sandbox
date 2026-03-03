#!/usr/bin/env bash
#
# dev.sh
# Local development orchestrator - starts all services in one terminal

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# SigNoz configuration - use persistent location
readonly SIGNOZ_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/agent-sandbox/signoz"
readonly SIGNOZ_COMPOSE_FILE="${SIGNOZ_DIR}/deploy/docker/docker-compose.yaml"

# Defaults
LLM_PROVIDER="${LLM_PROVIDER:-mock}"
RUN_FRONTEND=true
RUN_BACKEND=true
RUN_SIGNOZ=false
SIGNOZ_STOP=false
SIGNOZ_CREDS=false
RUN_OBSERVE=false

cleanup() {
  # Give child processes time to flush output
  sleep 2
  echo ""
  echo "All services stopped."
}

trap cleanup EXIT

usage() {
  echo "Usage: ${0##*/} [OPTIONS]"
  echo ""
  echo "Start all local development services with colored output."
  echo ""
  echo "Options:"
  echo "  --mock           Use mock LLM (fastest, no real responses)"
  echo "  --azure          Use Azure OpenAI (requires API keys)"
  echo "  --backend-only   Skip frontend service"
  echo "  --frontend-only  Skip backend services"
  echo "  --signoz         Start SigNoz for tracing (auto-configured)"
  echo "  --signoz-stop    Stop SigNoz containers and exit"
  echo "  --signoz-creds   Show SigNoz login credentials"
  echo "  --observe        Start lightweight OTLP dev collector (no Docker)"
  echo "  --help, -h       Show this help message"
  echo ""
  echo "Environment Variables:"
  echo "  LLM_PROVIDER     Override LLM provider (mock|azure)"
  exit 0
}

show_signoz_creds() {
  local creds="${HOME}/.config/agent-sandbox/signoz-credentials"
  if [[ -f "$creds" ]]; then
    echo "SigNoz Credentials:"
    grep -E "^SIGNOZ_" "$creds" | sed 's/SIGNOZ_/  /; s/="/: /; s/"$//'
  else
    echo "No credentials. Run ./scripts/setup-signoz.sh first."
  fi
}

start_signoz() {
  command -v docker &>/dev/null || { echo "ERROR: Docker required" >&2; exit 1; }

  if [[ ! -f "${SIGNOZ_COMPOSE_FILE}" ]]; then
    "${SCRIPT_DIR}/setup-signoz.sh"
    return
  fi

  if ! docker ps --format '{{.Names}}' | grep -q "signoz-otel-collector"; then
    docker compose -f "${SIGNOZ_COMPOSE_FILE}" up -d
    echo "Waiting for OTLP..."
    local i=0; while ! curl -s "http://localhost:4318/v1/traces" -d '{}' 2>/dev/null | grep -q "partialSuccess" && ((i++ < 30)); do sleep 1; done
  fi

  echo "SigNoz ready: http://localhost:8080 (--signoz-creds for login)"
}

stop_signoz() {
  echo "Stopping SigNoz..."

  if ! command -v docker &>/dev/null; then
    echo "ERROR: Docker is required but not installed" >&2
    exit 1
  fi

  if [[ ! -f "${SIGNOZ_COMPOSE_FILE}" ]]; then
    echo "SigNoz compose file not found. Nothing to stop."
    exit 0
  fi

  docker compose -f "${SIGNOZ_COMPOSE_FILE}" down
  echo "SigNoz stopped."
}

main() {
  # Unset VIRTUAL_ENV to prevent uv warnings about venv mismatch
  # Each project uses its own .venv, so we don't want the parent shell's venv
  unset VIRTUAL_ENV

  # Load backend/.env if it exists (for LLM_PROVIDER, Azure config, etc.)
  if [[ -f "${ROOT_DIR}/backend/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "${ROOT_DIR}/backend/.env"
    set +a
  fi

  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mock)
        LLM_PROVIDER="mock"
        shift
        ;;
      --azure)
        LLM_PROVIDER="azure"
        shift
        ;;
      --backend-only)
        RUN_FRONTEND=false
        shift
        ;;
      --frontend-only)
        RUN_BACKEND=false
        shift
        ;;
      --signoz)
        RUN_SIGNOZ=true
        shift
        ;;
      --signoz-stop)
        SIGNOZ_STOP=true
        shift
        ;;
      --signoz-creds)
        SIGNOZ_CREDS=true
        shift
        ;;
      --observe)
        RUN_OBSERVE=true
        shift
        ;;
      --help|-h)
        usage
        ;;
      *)
        echo "Unknown option: $1" >&2
        echo "Use --help for usage information" >&2
        exit 1
        ;;
    esac
  done

  export LLM_PROVIDER

  # Handle stop command
  if [[ "${SIGNOZ_STOP}" == "true" ]]; then
    stop_signoz
    exit 0
  fi

  # Handle credentials display
  if [[ "${SIGNOZ_CREDS}" == "true" ]]; then
    show_signoz_creds
    exit 0
  fi

  # Start SigNoz if requested
  if [[ "${RUN_SIGNOZ}" == "true" ]]; then
    start_signoz
    export VITE_OTEL_EXPORTER="otlp"
    # Use empty endpoint so browser uses relative URLs (/v1/traces) via Vite proxy
    export VITE_OTEL_ENDPOINT=""
    # Agent Framework HTTP exporters need full paths for each signal
    export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
    export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="http://localhost:4318/v1/traces"
    export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT="http://localhost:4318/v1/logs"
    export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT="http://localhost:4318/v1/metrics"
    # Enable Agent Framework instrumentation for traces
    export ENABLE_INSTRUMENTATION=true
    export OTEL_SERVICE_NAME="agent-sandbox-server"
  fi

  # Start lightweight dev collector if requested
  if [[ "${RUN_OBSERVE}" == "true" ]]; then
    export VITE_OTEL_EXPORTER="otlp"
    export VITE_OTEL_ENDPOINT=""
    export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
    export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="http://localhost:4318/v1/traces"
    export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT="http://localhost:4318/v1/logs"
    export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT="http://localhost:4318/v1/metrics"
    export ENABLE_INSTRUMENTATION=true
    export OTEL_SERVICE_NAME="agent-sandbox-server"
  fi

  # Build command array for concurrently
  local -a commands=()
  local -a names=()
  local -a colors=()

  if [[ "${RUN_BACKEND}" == "true" ]]; then
    # Start MCP servers first (they need to be ready before main server)
    commands+=("cd ${ROOT_DIR}/backend && uv run uvicorn agent_sandbox.text_mcp_server:mcp.http_app --factory --host 0.0.0.0 --port 8001 --reload")
    names+=("mcp:text")
    colors+=("cyan")

    commands+=("cd ${ROOT_DIR}/backend && uv run uvicorn agent_sandbox.number_mcp_server:mcp.http_app --factory --host 0.0.0.0 --port 8002 --reload")
    names+=("mcp:num")
    colors+=("magenta")

    commands+=("cd ${ROOT_DIR}/backend && uv run uvicorn agent_sandbox.demo_app_mcp_server:mcp.http_app --factory --host 0.0.0.0 --port 8003 --reload")
    names+=("mcp:app")
    colors+=("white")

    # Main server starts after MCP servers are healthy
    commands+=("until curl -sf http://localhost:8001/health && curl -sf http://localhost:8002/health && curl -sf http://localhost:8003/health; do sleep 1; done && cd ${ROOT_DIR}/backend && uv run uvicorn agent_sandbox.server:app --host 0.0.0.0 --port 8888 --reload")
    names+=("server")
    colors+=("blue")
  fi

  if [[ "${RUN_FRONTEND}" == "true" ]]; then
    commands+=("cd ${ROOT_DIR}/frontend && pnpm dev")
    names+=("frontend")
    colors+=("green")
  fi

  if [[ "${RUN_OBSERVE}" == "true" ]]; then
    commands+=("cd ${ROOT_DIR} && uv run --project collector uvicorn dev_collector.server:app --host 0.0.0.0 --port 4318 --reload")
    names+=("collector")
    colors+=("yellow")
  fi

  if [[ ${#commands[@]} -eq 0 ]]; then
    echo "No services to start (both backend and frontend disabled)" >&2
    exit 1
  fi

  # Join arrays with commas
  local names_str
  names_str="$(
    IFS=','
    echo "${names[*]}"
  )"
  local colors_str
  colors_str="$(
    IFS=','
    echo "${colors[*]}"
  )"

  echo "Starting services with LLM_PROVIDER=${LLM_PROVIDER}..."
  if [[ "${RUN_SIGNOZ}" == "true" ]]; then
    echo "SigNoz UI: http://localhost:8080"
  fi
  if [[ "${RUN_OBSERVE}" == "true" ]]; then
    echo "Observe dashboard: http://localhost:5173/observe"
  fi
  echo ""

  # Use pnpm dlx to run concurrently without installing it as a dependency
  pnpm dlx concurrently \
    --names "${names_str}" \
    --prefix-colors "${colors_str}" \
    --kill-others \
    "${commands[@]}" || true
}

main "$@"

#!/usr/bin/env bash
# setup-signoz.sh - SigNoz setup with auto-generated credentials
set -euo pipefail

readonly SIGNOZ_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/agent-sandbox/signoz"
readonly COMPOSE="${SIGNOZ_DIR}/deploy/docker/docker-compose.yaml"
readonly API="http://localhost:8080"
readonly CREDS="${HOME}/.config/agent-sandbox/signoz-credentials"

EMAIL="${SIGNOZ_ADMIN_EMAIL:-admin@localhost.dev}"
PASSWORD=""

log() { echo "[signoz] $1"; }

# Generate secure 12-char password with guaranteed character classes
generate_password() {
  local chars upper lower digit special
  # Generate required character classes
  upper=$(openssl rand -base64 12 | tr -dc 'A-Z' | head -c1)
  lower=$(openssl rand -base64 12 | tr -dc 'a-z' | head -c1)
  digit=$(openssl rand -base64 12 | tr -dc '0-9' | head -c1)
  special=$(shuf -e '@' '.' '_' '+' '-' -n1)
  # Generate 8 more random alphanumeric chars
  chars=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c8)
  # Combine and shuffle using array approach for reliability
  local all="${upper}${lower}${digit}${special}${chars}"
  echo "$all" | grep -o . | shuf | tr -d '\n'
}

# Wait for endpoint with timeout
wait_for() {
  local url=$1 max=${2:-30} i=0
  while ! curl -s "$url" &>/dev/null && ((i++ < max)); do sleep 1; done
  ((i < max))
}

# Load or generate credentials (stored in ~/.config/agent-sandbox/)
init_creds() {
  mkdir -p "$(dirname "$CREDS")" && chmod 700 "$(dirname "$CREDS")"
  if [[ -f "$CREDS" ]]; then
    # Safe parsing without source to prevent code injection
    EMAIL=$(grep '^SIGNOZ_EMAIL=' "$CREDS" | cut -d'"' -f2)
    PASSWORD=$(grep '^SIGNOZ_PASSWORD=' "$CREDS" | cut -d'"' -f2)
  else
    PASSWORD="$(generate_password)"
    printf 'SIGNOZ_EMAIL="%s"\nSIGNOZ_PASSWORD="%s"\n' "$EMAIL" "$PASSWORD" > "$CREDS"
    chmod 600 "$CREDS"
    log "Credentials saved to $CREDS"
  fi
}

# Register admin via API (tries both endpoints)
register() {
  local ver; ver=$(curl -s "$API/api/v1/version" 2>/dev/null || echo "{}")
  [[ "$ver" == *'"setupCompleted":true'* ]] && { log "Already configured"; return 0; }
  
  # Use jq to safely build JSON payload (prevents injection)
  local payload
  payload=$(jq -n --arg e "$EMAIL" --arg p "$PASSWORD" \
    '{email: $e, name: "Admin", password: $p, orgName: "LocalDev"}')
  for ep in register signup; do
    local resp; resp=$(curl -s -X POST "$API/api/v1/$ep" -H "Content-Type: application/json" -d "$payload" 2>/dev/null || echo "{}")
    [[ "$resp" == *accessJwt* || "$resp" == *success* ]] && { log "Admin created via /$ep"; return 0; }
  done
  log "WARNING: Could not verify account creation"
}

main() {
  [[ "${1:-}" == "--show-creds" ]] && { [[ -f "$CREDS" ]] && cat "$CREDS" || echo "No credentials. Run setup first."; exit 0; }
  
  command -v docker &>/dev/null || { log "ERROR: Docker required"; exit 1; }
  init_creds

  # Clone SigNoz if needed
  [[ -d "$SIGNOZ_DIR" ]] || git clone -b main --depth 1 https://github.com/SigNoz/signoz.git "$SIGNOZ_DIR"
  [[ -f "$COMPOSE" ]] || { log "ERROR: Compose file not found"; exit 1; }

  # Docker-in-docker DNS fix
  local override="${SIGNOZ_DIR}/deploy/docker/docker-compose.override.yaml"
  [[ -f "$override" ]] || cat > "$override" << 'EOF'
services:
  otel-collector: { dns: [127.0.0.11] }
  signoz: { dns: [127.0.0.11] }
  clickhouse: { dns: [127.0.0.11] }
  zookeeper-1: { dns: [127.0.0.11] }
  schema-migrator-sync: { dns: [127.0.0.11] }
  schema-migrator-async: { dns: [127.0.0.11] }
EOF

  # Add CORS for frontend (configurable via SIGNOZ_CORS_ORIGINS)
  local cors_origins="${SIGNOZ_CORS_ORIGINS:-http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000}"
  # Convert comma-separated to JSON array format
  local cors_json
  cors_json=$(echo "$cors_origins" | sed 's/,/","/g; s/^/["/; s/$/"]/')
  local cfg="${SIGNOZ_DIR}/deploy/docker/otel-collector-config.yaml"
  [[ -f "$cfg" ]] && ! grep -q "cors:" "$cfg" && \
    sed -i "s/      http:/      http:\n        cors:\n          allowed_origins: ${cors_json}\n          allowed_headers: [\"*\"]/" "$cfg"

  log "Starting containers..."
  docker compose -f "$COMPOSE" up -d

  log "Waiting for API..." && wait_for "$API/api/v1/version" 90
  register
  
  docker restart signoz-otel-collector &>/dev/null || true
  sleep 3
  log "Waiting for OTLP..." && wait_for "http://localhost:4318/v1/traces" 30 || log "WARNING: OTLP timeout"

  cat << EOF

SigNoz Ready!
  UI: http://localhost:8080 | OTLP: localhost:4318
  Login: $EMAIL / $PASSWORD
  Creds: ./scripts/dev.sh --signoz-creds
EOF
}

main "$@"

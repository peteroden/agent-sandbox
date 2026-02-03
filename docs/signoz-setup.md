# Observability Setup Guide

SigNoz is automatically set up during devcontainer creation with auto-registration.

## Quick Start

SigNoz is ready to use after the devcontainer starts:

- **UI**: http://localhost:8080
- **Credentials**: Auto-generated on first setup (see below)
- **OTLP HTTP**: http://localhost:4318
- **OTLP gRPC**: localhost:4317

To start dev servers with tracing enabled:

```bash
./scripts/dev.sh --signoz
```

## Retrieving Credentials

Credentials are auto-generated on first setup and saved securely:

```bash
# Show SigNoz login credentials
./scripts/dev.sh --signoz-creds
```

Credentials are stored in `~/.config/agent-sandbox/signoz-credentials` with restricted permissions (600).

## Manual Setup

If SigNoz isn't running, start it manually:

```bash
./scripts/setup-signoz.sh
```

This script:
1. Clones SigNoz if needed
2. Starts all containers
3. Auto-registers an admin account
4. Restarts the collector to enable OTLP via OpAMP

## Stopping SigNoz

```bash
./scripts/dev.sh --signoz-stop
```

## Environment Variables

Customize the admin email with environment variables (password is always auto-generated):

```bash
SIGNOZ_ADMIN_EMAIL=me@example.com ./scripts/setup-signoz.sh
```

## CORS Configuration

The OTel Collector must accept requests from the frontend origin. By default, SigNoz's collector allows all origins. For production deployments, configure specific origins in the collector config.

To customize CORS settings, edit the collector configuration:

```yaml
# In signoz/deploy/docker/otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
        cors:
          allowed_origins:
            - http://localhost:5173
            - https://your-production-domain.com
          allowed_headers:
            - Content-Type
            - X-Requested-With
```

Restart the collector after changes:

```bash
docker compose -f docker/docker-compose.yaml restart otel-collector
```

## Environment Variables

### Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_OTEL_EXPORTER` | Exporter type (`console` or `otlp`) | `console` |
| `VITE_OTEL_ENDPOINT` | OTLP collector URL | `http://localhost:4318` |
| `VITE_OTEL_SAMPLE_RATE` | Trace sampling ratio (0.0-1.0) | `1.0` |
| `VITE_SERVICE_NAME` | Service name for resource | `agent-sandbox-frontend` |

### Backend

| Variable | Description | Default |
|----------|-------------|---------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector URL | `http://localhost:4318` |
| `OTEL_SERVICE_NAME` | Service name for resource | `agent-sandbox-backend` |

## Verifying the Setup

1. Start services with tracing:

   ```bash
   ./scripts/dev.sh --signoz
   ```

2. Open the application at `http://localhost:5173`

3. Interact with the chat interface to generate traces

4. Open SigNoz UI at `http://localhost:8080`

5. Navigate to **Traces** to view distributed traces

## Troubleshooting

### No traces appearing

- Verify collector is running: `docker ps | grep signoz-otel-collector`
- Check collector logs: `docker logs signoz-otel-collector`
- Confirm backend has `OTEL_EXPORTER_OTLP_ENDPOINT` set
- Test endpoint: `curl -X POST http://localhost:4318/v1/traces -H "Content-Type: application/json" -d '{}'`

### Re-run setup

If SigNoz was misconfigured or the database was lost:

```bash
./scripts/dev.sh --signoz-stop
rm -rf /tmp/signoz
./scripts/setup-signoz.sh
```

## Resources

- [SigNoz Documentation](https://signoz.io/docs/)
- [SigNoz GitHub Repository](https://github.com/SigNoz/signoz)
- [OpenTelemetry Collector Configuration](https://opentelemetry.io/docs/collector/configuration/)

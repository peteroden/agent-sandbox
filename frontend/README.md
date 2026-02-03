# Frontend Skeleton

A Preact frontend application with Vite and AG-UI support.

## Tech Stack

- **Framework**: Preact with TypeScript
- **Build/Dev**: Vite
- **Styling**: Tailwind CSS
- **Routing**: Wouter
- **Testing**: Vitest with @testing-library/preact
- **Telemetry**: OpenTelemetry SDK for traces and logs
- **Backend Communication**: AG-UI protocol

## Getting Started

### Install Dependencies

```bash
pnpm install
```

### Development

```bash
pnpm dev
```

### Build

```bash
pnpm build
```

### Test

```bash
pnpm test        # Run tests in watch mode
pnpm test:ui     # Run tests with UI
```

### Preview Production Build

```bash
pnpm preview
```

## Project Structure

```text
frontend/
├── src/
│   ├── components/       # Reusable components
│   │   └── OTelErrorBoundary.tsx  # Error boundary with telemetry
│   ├── pages/            # Route pages
│   │   ├── Home.tsx
│   │   ├── Chat.tsx
│   │   └── Report.tsx
│   ├── hooks/            # Custom hooks
│   ├── services/         # Backend services
│   │   └── telemetry.ts  # OpenTelemetry service
│   ├── app.tsx           # Main app with routing
│   ├── app.css           # Tailwind CSS imports + app styles
│   └── main.tsx          # Entry point
├── test/                 # Test files
├── index.html
├── vite.config.ts
├── vitest.config.ts
└── package.json
```

## OpenTelemetry Configuration

The frontend uses vendor-neutral OpenTelemetry for Real User Monitoring (RUM). Telemetry includes traces, logs, and Web Vitals.

### Environment Variables

| Variable               | Default                   | Description                                      |
| ---------------------- | ------------------------- | ------------------------------------------------ |
| `VITE_OTEL_EXPORTER`   | `console`                 | Exporter type: `console` (dev) or `otlp` (prod)  |
| `VITE_OTEL_ENDPOINT`   | `http://localhost:4318`   | OTLP collector endpoint                          |
| `VITE_OTEL_SAMPLE_RATE`| `1.0`                     | Trace sampling ratio (0.0 to 1.0)                |
| `VITE_SERVICE_NAME`    | `agent-sandbox-frontend`  | Service name for attribution                     |

Copy `.env.example` to `.env.local` and configure as needed.

### Console Mode (Development)

By default, telemetry exports to the browser console for local development:

```bash
# .env.local
VITE_OTEL_EXPORTER=console
```

Open DevTools Console to see spans and logs.

### OTLP Mode (SigNoz/Production)

To export to SigNoz or another OTLP-compatible collector:

```bash
# .env.local
VITE_OTEL_EXPORTER=otlp
VITE_OTEL_ENDPOINT=http://localhost:4318
```

### CORS Requirements

When using OTLP mode, the collector must allow CORS from your frontend origin. For SigNoz, configure the CORS allowed origins in the collector config.

### Bundle Size Impact

OpenTelemetry adds approximately 90kb gzipped to the bundle (including Zone.js for async context propagation). This enables proper parent-child span linking across async operations.

### Telemetry API

```typescript
import { logger, pushEvent, withSpan, initWebVitals } from './services/telemetry';

// Structured logging
logger.info('User clicked button', { buttonId: 'submit' });
logger.error('Failed to fetch', { url: '/api/data' });

// Custom events
pushEvent('form_submit', { formId: 'contact' });

// Tracing
await withSpan('fetchData', async (span) => {
  span.setAttribute('url', '/api/data');
  return fetch('/api/data');
});

// Web Vitals (call once at startup)
initWebVitals();
```

## Features

### Routing

Routes are defined in `src/app.tsx`:

- `/` - Home page
- `/chat` - Chat interface
- `/report` - Report interface

### Error Boundary

The app is wrapped with `OTelErrorBoundary` which catches React errors and logs them to telemetry. Errors are rendered with a user-friendly fallback UI.

### AG-UI Integration

The AG-UI client service implements the event-based protocol for agent-UI communication.

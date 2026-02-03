import {
  trace,
  context,
  SpanStatusCode,
  type Tracer,
  type Span,
  type SpanOptions,
  type Attributes,
  metrics,
  type Meter,
} from '@opentelemetry/api';
import { logs, SeverityNumber, type Logger } from '@opentelemetry/api-logs';
import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { BatchSpanProcessor, SimpleSpanProcessor, ConsoleSpanExporter, TraceIdRatioBasedSampler } from '@opentelemetry/sdk-trace-base';
import { LoggerProvider, SimpleLogRecordProcessor, BatchLogRecordProcessor, ConsoleLogRecordExporter } from '@opentelemetry/sdk-logs';
import { MeterProvider, PeriodicExportingMetricReader, ConsoleMetricExporter } from '@opentelemetry/sdk-metrics';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { OTLPLogExporter } from '@opentelemetry/exporter-logs-otlp-http';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { type Resource, resourceFromAttributes, defaultResource } from '@opentelemetry/resources';
import { getWebAutoInstrumentations } from '@opentelemetry/auto-instrumentations-web';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { W3CTraceContextPropagator } from '@opentelemetry/core';
import { propagation } from '@opentelemetry/api';

// Re-export types and enums for convenience
export { SpanStatusCode };
export type { Span, SpanOptions, Attributes };

/** Log level string literals for API compatibility */
export type TelemetryLogLevel = 'trace' | 'debug' | 'info' | 'log' | 'warn' | 'error';

/** Log attributes type */
export type LogAttrs = Record<string, string | number | boolean>;

// Module state
let initialized = false;
let tracerProvider: WebTracerProvider | null = null;
let loggerProvider: LoggerProvider | null = null;
let meterProvider: MeterProvider | null = null;
let otelLogger: Logger | null = null;
let otelMeter: Meter | null = null;
let sessionId: string | null = null;
let currentUser: { id: string; attributes?: LogAttrs } | null = null;

const SERVICE_NAME = import.meta.env.VITE_SERVICE_NAME ?? 'agent-sandbox-frontend';
const SERVICE_VERSION = '1.0.0';
const SESSION_STORAGE_KEY = 'otel_session_id';

/**
 * Sanitize file paths to remove potential PII (usernames in paths).
 * Handles macOS, Linux, and Windows path formats.
 */
export function sanitizePath(path?: string): string {
  if (!path) return '';
  return path
    .replace(/\/Users\/[^/]+\//g, '/Users/***/')      // macOS
    .replace(/\/home\/[^/]+\//g, '/home/***/')        // Linux
    .replace(/[A-Z]:\\Users\\[^\\]+\\/gi, (match) => match.charAt(0) + ':\\Users\\***\\');  // Windows (any drive)
}

/**
 * Get or generate a session ID for this browser session.
 */
function getOrCreateSessionId(): string {
  const existing = sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) {
    return existing;
  }
  const newSessionId = crypto.randomUUID();
  sessionStorage.setItem(SESSION_STORAGE_KEY, newSessionId);
  return newSessionId;
}

/**
 * Create the OTel resource with service info and session ID.
 */
function createResource(): Resource {
  return defaultResource().merge(
    resourceFromAttributes({
      'service.name': SERVICE_NAME,
      'service.version': SERVICE_VERSION,
      'session.id': sessionId ?? '',
    })
  );
}

/**
 * Get the configured exporter type from environment.
 */
function getExporterType(): 'console' | 'otlp' {
  const exporter = import.meta.env.VITE_OTEL_EXPORTER ?? 'console';
  return exporter === 'otlp' ? 'otlp' : 'console';
}

/**
 * Get the OTLP endpoint from environment.
 * Uses relative path (proxied through Vite) in dev, or full URL in production.
 */
function getOtlpEndpoint(): string {
  const endpoint = import.meta.env.VITE_OTEL_ENDPOINT ?? 'http://localhost:4318';
  // In dev mode with Vite proxy, use relative paths to avoid CORS
  // The proxy forwards /v1/traces and /v1/logs to the OTLP collector
  if (import.meta.env.DEV && endpoint === 'http://localhost:4318') {
    return '';  // Use relative paths like /v1/traces
  }
  return endpoint;
}

/**
 * Get the sampling rate from environment.
 */
function getSampleRate(): number {
  const rate = parseFloat(import.meta.env.VITE_OTEL_SAMPLE_RATE ?? '1.0');
  return isNaN(rate) ? 1.0 : Math.max(0, Math.min(1, rate));
}

/**
 * Get the backend URL for trace context propagation.
 */
function getBackendUrl(): string {
  return import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8888';
}

/**
 * Flush telemetry data on page visibility change or unload.
 */
function handlePageUnload(): void {
  if (document.visibilityState === 'hidden') {
    tracerProvider?.forceFlush();
    loggerProvider?.forceFlush();
    meterProvider?.forceFlush();
  }
}

/**
 * Flush telemetry data on page hide (Safari fallback).
 */
function handlePageHide(): void {
  tracerProvider?.forceFlush();
  loggerProvider?.forceFlush();
  meterProvider?.forceFlush();
}

/**
 * Initialize OpenTelemetry for the frontend application.
 *
 * Sets up WebTracerProvider and LoggerProvider with configurable exporters
 * (console for dev, OTLP for production/SigNoz).
 */
export function initTelemetry(): void {
  if (initialized) return;

  try {
    // Get or create session ID
    sessionId = getOrCreateSessionId();

    const resource = createResource();
    let exporterType = getExporterType();
    const sampleRate = getSampleRate();

    // Validate OTLP endpoint URL when using OTLP exporter
    const endpoint = getOtlpEndpoint();
    if (exporterType === 'otlp' && endpoint) {
      try {
        new URL(endpoint);
      } catch {
        console.warn(`[Telemetry] Invalid OTLP endpoint URL: ${endpoint}, falling back to console exporter`);
        exporterType = 'console';
      }
    }

    // Build span processor based on exporter type
    const spanProcessor = exporterType === 'otlp'
      ? new BatchSpanProcessor(new OTLPTraceExporter({
          url: `${endpoint}/v1/traces`,
        }))
      : new SimpleSpanProcessor(new ConsoleSpanExporter());

    // Configure tracer provider with processor in constructor
    tracerProvider = new WebTracerProvider({
      resource,
      sampler: new TraceIdRatioBasedSampler(sampleRate),
      spanProcessors: [spanProcessor],
    });

    // Register the tracer provider with ZoneContextManager for async context
    tracerProvider.register({
      contextManager: new ZoneContextManager(),
    });

    // Build log processor based on exporter type
    const logProcessor = exporterType === 'otlp'
      ? new BatchLogRecordProcessor(new OTLPLogExporter({
          url: `${endpoint}/v1/logs`,
        }))
      : new SimpleLogRecordProcessor(new ConsoleLogRecordExporter());

    // Configure logger provider with processor in constructor
    loggerProvider = new LoggerProvider({
      resource,
      processors: [logProcessor],
    });

    // Register the logger provider globally
    logs.setGlobalLoggerProvider(loggerProvider);

    // Get our logger instance
    otelLogger = loggerProvider.getLogger(SERVICE_NAME, SERVICE_VERSION);

    // Build metric reader based on exporter type
    const metricReader = exporterType === 'otlp'
      ? new PeriodicExportingMetricReader({
          exporter: new OTLPMetricExporter({
            url: `${endpoint}/v1/metrics`,
          }),
          exportIntervalMillis: 10000,
        })
      : new PeriodicExportingMetricReader({
          exporter: new ConsoleMetricExporter(),
          exportIntervalMillis: 60000,
        });

    // Configure meter provider
    meterProvider = new MeterProvider({
      resource,
      readers: [metricReader],
    });

    // Register the meter provider globally
    metrics.setGlobalMeterProvider(meterProvider);

    // Get our meter instance
    otelMeter = meterProvider.getMeter(SERVICE_NAME, SERVICE_VERSION);

    // Configure W3C TraceContext propagator for distributed tracing
    propagation.setGlobalPropagator(new W3CTraceContextPropagator());

    // Register auto-instrumentations with CORS trace header propagation
    const backendUrl = getBackendUrl();
    registerInstrumentations({
      tracerProvider,
      instrumentations: [
        getWebAutoInstrumentations({
          '@opentelemetry/instrumentation-document-load': {},
          '@opentelemetry/instrumentation-fetch': {
            // Propagate trace headers for both direct backend and /api proxy
            propagateTraceHeaderCorsUrls: [
              new RegExp(backendUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
              /localhost:8888/,
              /127\.0\.0\.1:8888/,
              /\/api/,  // Match /api proxy path (same-origin, headers always sent)
            ],
            clearTimingResources: true,
          },
          '@opentelemetry/instrumentation-xml-http-request': {
            // Same CORS propagation for XHR
            propagateTraceHeaderCorsUrls: [
              new RegExp(backendUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
              /localhost:8888/,
              /127\.0\.0\.1:8888/,
              /\/api/,  // Match /api proxy path
            ],
          },
          '@opentelemetry/instrumentation-user-interaction': {},
        }),
      ],
    });

    // Register page unload handlers for data flushing
    document.addEventListener('visibilitychange', handlePageUnload);
    window.addEventListener('pagehide', handlePageHide);

    initialized = true;

    // Log initialization in dev mode for debugging
    if (import.meta.env.DEV) {
      console.log('[Telemetry] Initialized:', {
        exporter: exporterType,
        endpoint: endpoint || '(Vite proxy)',
        sampleRate,
        sessionId,
      });
    }
  } catch (error) {
    // Graceful degradation - log to console but don't crash
    console.warn('Failed to initialize telemetry:', error);
    initialized = false;
  }
}

/**
 * Check if telemetry was successfully initialized.
 */
export function isInitialized(): boolean {
  return initialized;
}

/**
 * Shutdown telemetry and clean up resources.
 * Call this before tests or when unmounting the application.
 */
export async function shutdownTelemetry(): Promise<void> {
  if (!initialized) return;

  // Remove event listeners
  document.removeEventListener('visibilitychange', handlePageUnload);
  window.removeEventListener('pagehide', handlePageHide);

  // Shutdown providers (they may return promises)
  await Promise.all([
    tracerProvider?.shutdown(),
    loggerProvider?.shutdown(),
    meterProvider?.shutdown(),
  ]);

  // Reset state to allow re-initialization
  tracerProvider = null;
  loggerProvider = null;
  meterProvider = null;
  otelLogger = null;
  otelMeter = null;
  initialized = false;
}

/**
 * Get the current session ID.
 */
export function getSessionId(): string | null {
  return sessionId;
}

/**
 * Get the tracer for creating custom spans.
 *
 * @returns A tracer instance for creating spans.
 */
export function getTracer(): Tracer {
  return trace.getTracer(SERVICE_NAME, SERVICE_VERSION);
}

// =============================================================================
// Structured Logger
// =============================================================================

/**
 * Emit a log record with the given severity.
 */
function emitLog(severityNumber: SeverityNumber, message: string, attrs?: LogAttrs): void {
  if (!otelLogger) return;

  otelLogger.emit({
    severityNumber,
    body: message,
    attributes: attrs,
  });
}

/**
 * Structured logger wrapping the OTel Logs API.
 */
export const logger = {
  debug: (msg: string, attrs?: LogAttrs): void => emitLog(SeverityNumber.DEBUG, msg, attrs),
  info: (msg: string, attrs?: LogAttrs): void => emitLog(SeverityNumber.INFO, msg, attrs),
  warn: (msg: string, attrs?: LogAttrs): void => emitLog(SeverityNumber.WARN, msg, attrs),
  error: (msg: string, attrs?: LogAttrs): void => emitLog(SeverityNumber.ERROR, msg, attrs),
};

// =============================================================================
// Legacy API Surface (for backwards compatibility)
// =============================================================================

/**
 * Map legacy log level strings to OTel severity numbers.
 */
function mapLogLevel(level: TelemetryLogLevel): SeverityNumber {
  switch (level) {
    case 'trace':
      return SeverityNumber.TRACE;
    case 'debug':
      return SeverityNumber.DEBUG;
    case 'info':
    case 'log':
      return SeverityNumber.INFO;
    case 'warn':
      return SeverityNumber.WARN;
    case 'error':
      return SeverityNumber.ERROR;
    default:
      return SeverityNumber.INFO;
  }
}

/**
 * Push a custom event with optional attributes.
 *
 * @param name - Event name (e.g., 'button_click', 'form_submit')
 * @param attributes - Optional key-value pairs for event context
 */
export function pushEvent(
  name: string,
  attributes?: LogAttrs
): void {
  if (!otelLogger) return;

  otelLogger.emit({
    severityNumber: SeverityNumber.INFO,
    body: name,
    attributes: {
      'event.name': name,
      ...attributes,
    },
  });
}

/**
 * Push an error with optional context.
 *
 * @param error - The error to push
 * @param errorContext - Optional context about where/why the error occurred
 */
export function pushError(
  error: Error,
  errorContext?: LogAttrs
): void {
  if (!otelLogger) return;

  // Sanitize error stack to remove potential PII (file paths with usernames)
  const sanitizedStack = sanitizePath(error.stack);

  otelLogger.emit({
    severityNumber: SeverityNumber.ERROR,
    body: error.message,
    attributes: {
      'error.type': error.name,
      'error.stack': sanitizedStack,
      ...errorContext,
    },
  });
}

/**
 * Set the current user for session attribution.
 *
 * @param id - Unique user identifier
 * @param attributes - Optional user attributes (email, role, etc.)
 */
export function setUser(
  id: string,
  attributes?: LogAttrs
): void {
  currentUser = { id, attributes };
}

/**
 * Clear the current user (e.g., on logout).
 */
export function clearUser(): void {
  currentUser = null;
}

/**
 * Get the current user info.
 */
export function getCurrentUser(): { id: string; attributes?: LogAttrs } | null {
  return currentUser;
}

/**
 * Push a measurement/metric with numeric values.
 *
 * @param type - Measurement type (e.g., 'api_latency', 'memory_usage')
 * @param values - Numeric values to record
 * @param measurementContext - Optional context for the measurement
 */
export function pushMeasurement(
  type: string,
  values: Record<string, number>,
  measurementContext?: LogAttrs
): void {
  if (!otelLogger) return;

  // Convert values to prefixed attributes
  const valueAttrs: Record<string, number> = {};
  for (const [key, value] of Object.entries(values)) {
    valueAttrs[`measurement.${key}`] = value;
  }

  otelLogger.emit({
    severityNumber: SeverityNumber.INFO,
    body: type,
    attributes: {
      'measurement.type': type,
      ...valueAttrs,
      ...measurementContext,
    },
  });
}

/**
 * Push a structured log message.
 *
 * @param message - Log message
 * @param level - Log level (default: 'info')
 * @param logContext - Optional context for the log
 */
export function pushLog(
  message: string,
  level: TelemetryLogLevel = 'info',
  logContext?: LogAttrs
): void {
  if (!otelLogger) return;

  otelLogger.emit({
    severityNumber: mapLogLevel(level),
    body: message,
    attributes: logContext,
  });
}

// =============================================================================
// Span Helpers
// =============================================================================

/**
 * Start a new span for tracing an operation.
 *
 * Remember to call span.end() when the operation is complete.
 * For automatic span management, use withSpan() instead.
 *
 * @param name - Name of the span/operation
 * @param options - Optional span options (attributes, links, etc.)
 * @returns The created span
 */
export function startSpan(name: string, options?: SpanOptions): Span {
  return getTracer().startSpan(name, options);
}

/**
 * Get the currently active span, if any.
 *
 * @returns The active span or undefined if none is active
 */
export function getActiveSpan(): Span | undefined {
  return trace.getActiveSpan();
}

/**
 * Execute a function within a span context.
 *
 * Automatically:
 * - Creates and starts the span
 * - Sets the span as active in the context
 * - Records exceptions if the function throws
 * - Sets error status on failure
 * - Ends the span when complete
 *
 * @param name - Name of the span/operation
 * @param fn - Function to execute (receives the span as argument)
 * @returns The result of the function
 */
export async function withSpan<T>(
  name: string,
  fn: (span: Span) => T | Promise<T>
): Promise<T> {
  const span = startSpan(name);

  try {
    const result = await context.with(
      trace.setSpan(context.active(), span),
      () => fn(span)
    );
    span.setStatus({ code: SpanStatusCode.OK });
    return result;
  } catch (error) {
    span.recordException(error as Error);
    span.setStatus({
      code: SpanStatusCode.ERROR,
      message: (error as Error).message,
    });
    throw error;
  } finally {
    span.end();
  }
}

/**
 * Add an event to the currently active span.
 *
 * Does nothing if no span is active.
 *
 * @param name - Event name
 * @param attributes - Optional event attributes
 */
export function addSpanEvent(
  name: string,
  attributes?: Attributes
): void {
  const span = getActiveSpan();
  span?.addEvent(name, attributes);
}

// =============================================================================
// Web Vitals
// =============================================================================

/**
 * Initialize Web Vitals monitoring.
 *
 * Reports Core Web Vitals (CLS, INP, LCP, FCP, TTFB) as metrics using histograms.
 */
export function initWebVitals(): void {
  if (!otelMeter) return;

  // Create histograms for each web vital
  const clsHistogram = otelMeter.createHistogram('web_vital.cls', {
    description: 'Cumulative Layout Shift',
    unit: 'score',
  });
  const inpHistogram = otelMeter.createHistogram('web_vital.inp', {
    description: 'Interaction to Next Paint',
    unit: 'ms',
  });
  const lcpHistogram = otelMeter.createHistogram('web_vital.lcp', {
    description: 'Largest Contentful Paint',
    unit: 'ms',
  });
  const fcpHistogram = otelMeter.createHistogram('web_vital.fcp', {
    description: 'First Contentful Paint',
    unit: 'ms',
  });
  const ttfbHistogram = otelMeter.createHistogram('web_vital.ttfb', {
    description: 'Time to First Byte',
    unit: 'ms',
  });

  const histograms: Record<string, ReturnType<typeof otelMeter.createHistogram>> = {
    CLS: clsHistogram,
    INP: inpHistogram,
    LCP: lcpHistogram,
    FCP: fcpHistogram,
    TTFB: ttfbHistogram,
  };

  // Dynamically import web-vitals to avoid issues in test environments
  import('web-vitals').then(({ onCLS, onINP, onLCP, onFCP, onTTFB }) => {
    const report = (metric: { name: string; value: number; id: string }) => {
      const histogram = histograms[metric.name];
      if (histogram) {
        histogram.record(metric.value, { 'web_vital.id': metric.id });
        if (import.meta.env.DEV) {
          console.log('[WebVital]', metric.name, metric.value);
        }
      }
    };

    onCLS(report);
    onINP(report);
    onLCP(report);
    onFCP(report);
    onTTFB(report);
  }).catch(() => {
    // Ignore errors in environments where web-vitals doesn't work
  });
}

// =============================================================================
// Test Helpers (exported for testing only)
// =============================================================================

/**
 * @internal Get the internal OTel logger for testing.
 */
export function _getLoggerForTest(): Logger | null {
  return otelLogger;
}

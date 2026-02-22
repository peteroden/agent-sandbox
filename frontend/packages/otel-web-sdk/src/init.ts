/**
 * @fileoverview SDK initialization module.
 *
 * Sets up OpenTelemetry providers (Trace, Log, Metrics), registers
 * auto-instrumentations, and configures global error handlers.
 */
import {
  context,
  propagation,
  metrics,
} from '@opentelemetry/api'
import { logs } from '@opentelemetry/api-logs'
import { WebTracerProvider } from '@opentelemetry/sdk-trace-web'
import {
  BatchSpanProcessor,
  SimpleSpanProcessor,
  ConsoleSpanExporter,
  TraceIdRatioBasedSampler,
} from '@opentelemetry/sdk-trace-base'
import {
  LoggerProvider,
  SimpleLogRecordProcessor,
  BatchLogRecordProcessor,
  ConsoleLogRecordExporter,
} from '@opentelemetry/sdk-logs'
import {
  MeterProvider,
  PeriodicExportingMetricReader,
  ConsoleMetricExporter,
} from '@opentelemetry/sdk-metrics'
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http'
import { OTLPLogExporter } from '@opentelemetry/exporter-logs-otlp-http'
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http'
import { ZoneContextManager } from '@opentelemetry/context-zone'
import { resourceFromAttributes, defaultResource } from '@opentelemetry/resources'
import { getWebAutoInstrumentations } from '@opentelemetry/auto-instrumentations-web'
import { registerInstrumentations } from '@opentelemetry/instrumentation'
import { W3CTraceContextPropagator } from '@opentelemetry/core'

// Module state
let initialized = false
let debugMode = false
let tracerProvider: WebTracerProvider | null = null
let loggerProvider: LoggerProvider | null = null
let meterProvider: MeterProvider | null = null
let sessionId: string | null = null

const SESSION_STORAGE_KEY = 'otel_session_id'

/**
 * SDK initialization options.
 */
export interface InitOptions {
  /** Service name for resource attributes */
  serviceName: string
  /** OTLP endpoint URL. Empty string uses console exporter. */
  endpoint: string
  /** Service version (default: '1.0.0') */
  serviceVersion?: string
  /** Sampling rate 0.0-1.0 (default: 1.0) */
  sampleRate?: number
  /** URLs to propagate trace headers to (CORS) */
  corsUrls?: Array<string | RegExp>
  /** Enable debug logging to console */
  debug?: boolean
}

/**
 * Generate a fallback UUID for environments without crypto.randomUUID.
 */
function generateFallbackUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

/**
 * Get or generate a session ID for this browser session.
 */
function getOrCreateSessionId(): string {
  try {
    const existing = sessionStorage.getItem(SESSION_STORAGE_KEY)
    if (existing) {
      return existing
    }
    const newSessionId = typeof crypto?.randomUUID === 'function'
      ? crypto.randomUUID()
      : generateFallbackUUID()
    sessionStorage.setItem(SESSION_STORAGE_KEY, newSessionId)
    return newSessionId
  } catch {
    // sessionStorage may not be available in some environments
    return typeof crypto?.randomUUID === 'function'
      ? crypto.randomUUID()
      : generateFallbackUUID()
  }
}

/**
 * Create the OTel resource with service info and session ID.
 */
function createResource(serviceName: string, serviceVersion: string) {
  return defaultResource().merge(
    resourceFromAttributes({
      'service.name': serviceName,
      'service.version': serviceVersion,
      'session.id': sessionId ?? '',
    })
  )
}

/**
 * Sanitize file paths to remove potential PII (usernames in paths).
 * Handles both regular paths and URL-encoded paths.
 */
export function sanitizePath(path?: string): string {
  if (!path) return ''
  return path
    .replace(/\/Users\/[^/]+\//g, '/Users/***/')      // macOS
    .replace(/\/home\/[^/]+\//g, '/home/***/')        // Linux
    .replace(/[A-Z]:\\Users\\[^\\]+\\/gi, (match) =>
      match.charAt(0) + ':\\Users\\***\\'
    )  // Windows
    .replace(/%2F(Users|home)%2F[^%]+%2F/gi, '%2F$1%2F***%2F')  // URL-encoded
}

// Store original error handler to chain
let originalOnError: OnErrorEventHandler = null

/**
 * Global error handler for window.onerror.
 */
function handleGlobalError(
  message: string | Event,
  source?: string,
  lineno?: number,
  colno?: number,
  error?: Error
): boolean {
  const logger = loggerProvider?.getLogger('global-errors')
  if (logger) {
    const sanitizedStack = error?.stack ? sanitizePath(error.stack) : ''
    const sanitizedSource = source ? sanitizePath(source) : ''

    logger.emit({
      severityNumber: 17, // ERROR
      body: typeof message === 'string' ? message : 'Unknown error',
      attributes: {
        'error.type': error?.name ?? 'Error',
        'error.stack': sanitizedStack,
        'error.source': sanitizedSource,
        'error.lineno': lineno ?? 0,
        'error.colno': colno ?? 0,
      },
      context: context.active(),
    })
  }
  // Chain to original handler if it exists
  if (typeof originalOnError === 'function') {
    return originalOnError(message, source, lineno, colno, error)
  }
  return false // Don't suppress the error
}

/**
 * Global handler for unhandled promise rejections.
 */
function handleUnhandledRejection(event: PromiseRejectionEvent): void {
  const logger = loggerProvider?.getLogger('global-errors')
  if (logger) {
    const error = event.reason as Error | undefined
    const sanitizedStack = error?.stack ? sanitizePath(error.stack) : ''

    logger.emit({
      severityNumber: 17, // ERROR
      body: error?.message ?? 'Unhandled promise rejection',
      attributes: {
        'error.type': 'UnhandledPromiseRejection',
        'error.reason_type': error?.name ?? typeof event.reason,
        'error.stack': sanitizedStack,
      },
      context: context.active(),
    })
  }
}

/**
 * Flush telemetry data on page visibility change or unload.
 */
function handlePageUnload(): void {
  if (document.visibilityState === 'hidden') {
    tracerProvider?.forceFlush()
    loggerProvider?.forceFlush()
    meterProvider?.forceFlush()
  }
}

/**
 * Initialize the OpenTelemetry SDK.
 *
 * @param options - Configuration options
 */
export function init(options: InitOptions): void {
  if (initialized) return

  try {
    const {
      serviceName,
      endpoint,
      serviceVersion = '1.0.0',
      sampleRate = 1.0,
      corsUrls = [],
      debug = false,
    } = options

    // Get or create session ID
    sessionId = getOrCreateSessionId()

    const resource = createResource(serviceName, serviceVersion)
    
    // Determine if using OTLP or console exporter
    // - 'console' or missing endpoint → console exporter
    // - Any other value (including empty string for relative URLs) → OTLP
    const useConsole = endpoint === 'console'
    
    // Build the base URL for OTLP exporters
    // Empty string means relative URLs (for Vite proxy)
    const otlpBaseUrl = useConsole ? '' : endpoint

    // Build span processor based on exporter type
    const spanProcessor = useConsole
      ? new SimpleSpanProcessor(new ConsoleSpanExporter())
      : new BatchSpanProcessor(new OTLPTraceExporter({
          url: `${otlpBaseUrl}/v1/traces`,
        }))

    // Configure tracer provider
    tracerProvider = new WebTracerProvider({
      resource,
      sampler: new TraceIdRatioBasedSampler(sampleRate),
      spanProcessors: [spanProcessor],
    })

    // Register with ZoneContextManager for async context
    tracerProvider.register({
      contextManager: new ZoneContextManager(),
    })

    // Build log processor
    const logProcessor = useConsole
      ? new SimpleLogRecordProcessor(new ConsoleLogRecordExporter())
      : new BatchLogRecordProcessor(new OTLPLogExporter({
          url: `${otlpBaseUrl}/v1/logs`,
        }))

    // Configure logger provider
    loggerProvider = new LoggerProvider({
      resource,
      processors: [logProcessor],
    })
    logs.setGlobalLoggerProvider(loggerProvider)

    // Build metric reader
    const metricReader = useConsole
      ? new PeriodicExportingMetricReader({
          exporter: new ConsoleMetricExporter(),
          exportIntervalMillis: 60000,
        })
      : new PeriodicExportingMetricReader({
          exporter: new OTLPMetricExporter({
            url: `${otlpBaseUrl}/v1/metrics`,
          }),
          exportIntervalMillis: 10000,
        })

    // Configure meter provider
    meterProvider = new MeterProvider({
      resource,
      readers: [metricReader],
    })
    metrics.setGlobalMeterProvider(meterProvider)

    // Configure propagator
    propagation.setGlobalPropagator(new W3CTraceContextPropagator())

    // Register auto-instrumentations
    registerInstrumentations({
      tracerProvider,
      instrumentations: [
        getWebAutoInstrumentations({
          '@opentelemetry/instrumentation-document-load': {},
          '@opentelemetry/instrumentation-fetch': {
            propagateTraceHeaderCorsUrls: corsUrls,
            clearTimingResources: true,
          },
          '@opentelemetry/instrumentation-xml-http-request': {
            propagateTraceHeaderCorsUrls: corsUrls,
          },
          '@opentelemetry/instrumentation-user-interaction': {},
        }),
      ],
    })

    // Register global error handlers (chain with existing)
    originalOnError = window.onerror
    window.onerror = handleGlobalError
    window.addEventListener('unhandledrejection', handleUnhandledRejection)

    // Register page unload handlers
    document.addEventListener('visibilitychange', handlePageUnload)
    window.addEventListener('pagehide', handlePageUnload)

    initialized = true
    debugMode = debug

    if (debugMode) {
      console.log('[OTel SDK] Initialized:', {
        serviceName,
        endpoint: useConsole ? '(console)' : (otlpBaseUrl || '(relative URLs)'),
        sampleRate,
        sessionId,
      })
    }
  } catch (error) {
    console.warn('[OTel SDK] Initialization failed:', error)
    initialized = false
  }
}

/**
 * Check if the SDK is initialized.
 */
export function isInitialized(): boolean {
  return initialized
}

/**
 * Get the current session ID.
 */
export function getSessionId(): string | null {
  return sessionId
}

/**
 * Get the tracer provider for internal use.
 * @internal
 */
export function _getTracerProvider(): WebTracerProvider | null {
  return tracerProvider
}

/**
 * Get the logger provider for internal use.
 * @internal
 */
export function _getLoggerProvider(): LoggerProvider | null {
  return loggerProvider
}

/**
 * Get the meter provider for internal use.
 * @internal
 */
export function _getMeterProvider(): MeterProvider | null {
  return meterProvider
}

/**
 * Check if debug mode is enabled.
 * @internal
 */
export function _isDebug(): boolean {
  return debugMode
}

/**
 * Shutdown the SDK and clean up resources.
 */
export async function shutdown(): Promise<void> {
  if (!initialized) return

  // Remove event listeners
  window.onerror = originalOnError
  originalOnError = null
  window.removeEventListener('unhandledrejection', handleUnhandledRejection)
  document.removeEventListener('visibilitychange', handlePageUnload)
  window.removeEventListener('pagehide', handlePageUnload)

  // Clear header injection
  delete (globalThis as Record<string, unknown>).__otelInjectHeaders

  // Shutdown providers (use allSettled to ensure all cleanup completes)
  await Promise.allSettled([
    tracerProvider?.shutdown(),
    loggerProvider?.shutdown(),
    meterProvider?.shutdown(),
  ])

  // Reset state
  tracerProvider = null
  loggerProvider = null
  meterProvider = null
  debugMode = false
  initialized = false
}

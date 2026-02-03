"""OpenTelemetry configuration for MCP servers."""

import logging
import os
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


def configure_mcp_telemetry(service_name: str) -> None:
    """Configure OpenTelemetry for MCP servers.

    Sets up TracerProvider and LoggerProvider with the specified service name.
    Configures exporters based on environment variables:

    - OTEL_EXPORTER_OTLP_ENDPOINT: When set, sends traces and logs via OTLP HTTP
    - ENABLE_CONSOLE_EXPORTERS: When 'true', '1', or 'yes', also logs spans to console

    Also configures W3C TraceContext propagation for extracting traceparent headers.

    Note: Call instrument_mcp_app() AFTER creating the FastMCP instance.

    Args:
        service_name: The name of the service for trace identification.
    """
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")

    # OTLP trace exporter for SigNoz/collectors
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        otlp_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info("OTLP trace exporter configured for %s", otlp_endpoint)

    # Console exporter for debugging
    if os.environ.get("ENABLE_CONSOLE_EXPORTERS", "").lower() in ("true", "1", "yes"):
        # Use SimpleSpanProcessor for immediate console output (no batching delay)
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)

    # OTLP log exporter for SigNoz/collectors
    if otlp_endpoint:
        from opentelemetry._logs import get_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.sdk._logs import LoggerProvider as SDKLoggerProvider

        # Only set up logger provider if not already configured
        current_provider = get_logger_provider()
        if not isinstance(current_provider, SDKLoggerProvider):
            log_provider = LoggerProvider(resource=resource)
            log_exporter = OTLPLogExporter(endpoint=f"{otlp_endpoint}/v1/logs")
            log_provider.add_log_record_processor(
                BatchLogRecordProcessor(log_exporter))
            set_logger_provider(log_provider)

            # Attach handler to root logger to capture Python logs
            handler = LoggingHandler(
                level=logging.INFO, logger_provider=log_provider)
            logging.getLogger().addHandler(handler)
            logger.info("OTLP log exporter configured for %s", otlp_endpoint)

    # Configure W3C TraceContext propagation for extracting traceparent headers
    set_global_textmap(TraceContextTextMapPropagator())


def instrument_mcp_app(app: "FastAPI | None" = None) -> None:
    """Instrument Starlette/FastAPI for HTTP tracing.

    Must be called AFTER creating the FastAPI/FastMCP instance so the
    app exists to be instrumented.

    Args:
        app: The FastAPI app instance to instrument. If None, uses global
             instrumentation which may not properly extract trace context.
    """
    from opentelemetry.instrumentation.starlette import StarletteInstrumentor

    instrumentor = StarletteInstrumentor()

    if app is not None:
        # Instrument the specific app instance for proper context extraction
        StarletteInstrumentor.instrument_app(app)
        logger.info("Instrumented FastAPI app for tracing")
    else:
        # Fallback to global instrumentation (patches Starlette class)
        # Check if already instrumented to avoid double-patching
        if not instrumentor.is_instrumented_by_opentelemetry:
            instrumentor.instrument()
            logger.info("Using global Starlette instrumentation")
        else:
            logger.debug("Starlette already instrumented, skipping")


def get_tracer() -> trace.Tracer:
    """Get tracer for custom spans.

    Returns a tracer instance that can be used to create custom spans
    for instrumenting application code.

    Returns:
        A tracer instance for creating spans.
    """
    return trace.get_tracer("agent_sandbox")

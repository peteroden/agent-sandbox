"""OpenTelemetry configuration for MCP servers."""

import logging
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from mcp.server.lowlevel.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.starlette import StarletteInstrumentor
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
from starlette.applications import Starlette
from starlette.routing import Route

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


# Type alias for ASGI app
ASGIApp = Callable[[Any, Any, Any], Any]


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
            root_logger = logging.getLogger()
            # Ensure root logger level is set
            root_logger.setLevel(logging.INFO)
            handler = LoggingHandler(
                level=logging.INFO, logger_provider=log_provider)
            root_logger.addHandler(handler)
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


def create_instrumented_mcp_asgi(
    mcp_server: Server[Any, Any],
    *,
    stateless: bool = False,
) -> tuple[Starlette, StreamableHTTPSessionManager]:
    """Create an instrumented ASGI app from an MCP Server.

    Wraps the MCP Server in a StreamableHTTPSessionManager and exposes it
    as a Starlette app that can be mounted on FastAPI.

    Important: The caller is responsible for running the session_manager
    within their application's lifespan context using:
        async with aclosing(session_manager.run()):
            yield

    Optionally instruments the app for OpenTelemetry tracing when
    OTEL_EXPORTER_OTLP_ENDPOINT is set.

    Args:
        mcp_server: The MCP Server instance (from agent.as_mcp_server())
        stateless: Whether to use stateless sessions (default False)

    Returns:
        A tuple of (Starlette app, session_manager) - the session_manager
        must be run within the parent app's lifespan.
    """
    # Create session manager (handles request/response lifecycle)
    session_manager = StreamableHTTPSessionManager(
        app=mcp_server,
        event_store=None,
        json_response=False,
        stateless=stateless,
    )

    # Create ASGI app that wraps the session manager
    streamable_http_app = StreamableHTTPASGIApp(session_manager)

    # Create Starlette app for routing
    starlette_app = Starlette(
        routes=[
            Route("/", endpoint=streamable_http_app),
        ],
    )

    # Instrument for tracing if OTEL is enabled
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        StarletteInstrumentor.instrument_app(starlette_app)
        logger.info("Instrumented MCP ASGI app for tracing")

    return starlette_app, session_manager

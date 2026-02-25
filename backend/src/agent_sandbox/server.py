"""AG-UI server for Agent Sandbox."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.observability import configure_otel_providers, get_tracer
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.starlette import StarletteInstrumentor
from starlette.applications import Starlette
from starlette.routing import Route

from agent_sandbox.agents.mock_chat_client import MockChatClient
from agent_sandbox.registry.mcp_registry import MCPServerRegistry

# Configure OpenTelemetry using Agent Framework (must be done BEFORE app creation)
# Reads from environment: ENABLE_INSTRUMENTATION, OTEL_EXPORTER_OTLP_*_ENDPOINT
configure_otel_providers()

# Bridge Python logging to OTel so log records are exported with trace context
if os.environ.get("ENABLE_INSTRUMENTATION", "").lower() == "true":
    from opentelemetry._logs import get_logger_provider
    from opentelemetry.sdk._logs import LoggingHandler

    otel_handler = LoggingHandler(
        level=logging.INFO,
        logger_provider=get_logger_provider(),
    )
    logging.getLogger().addHandler(otel_handler)
    logging.getLogger().setLevel(logging.INFO)

# Set up logging
logger = logging.getLogger(__name__)
tracer = get_tracer()


# Agent configuration
AGENT_NAME = "AGUIAssistant"
AGENT_INSTRUCTIONS = """You are AGUIAssistant with access to tools.

CRITICAL RULES FOR TOOL RESULTS:
- When you call a tool, DO NOT produce a user answer yet - wait for the result
- After tool results arrive, you MUST use them VERBATIM - do not invent or hallucinate values
- NEVER make up a result - only report exactly what the tool returned
- If a tool returns "8", your response is "8" - not a guess, not a calculation
- If a tool result message contains `text`, respond with that exact `text` value and nothing else
- Do not rephrase, recompute, or restate tool results. The tool result is authoritative
- If multiple tool result chunks arrive, return the first `text` value
- If no tool result arrives, say you cannot produce an answer
- If a tool was called, the ONLY valid final message is the tool result `text` (verbatim). No summaries, no reasoning, no extra words.
- Do NOT perform math yourself when a math tool was called. Use the tool result only.

DECISION PROCESS:
1. Does the user want to do MATH (add, subtract, sum, plus, minus, total, difference)?
   -> YES: Use add_numbers or subtract_numbers tool
   -> NO: Continue to step 2

2. Does the user want to REPEAT or ECHO text?
   -> YES: Use echo_text tool
   -> NO: Respond conversationally without tools

AVAILABLE TOOLS:
- add_numbers(a: int, b: int): Returns a + b. Keywords: add, plus, sum, total
- subtract_numbers(a: int, b: int): Returns a - b. Keywords: subtract, minus, difference
- echo_text(message: str): Repeats text. Keywords: echo, repeat, say

EXTRACT PARAMETERS:
- Identify which tool to use based on user intent
- Extract parameters from user input according to tool definitions

RESPONSE FORMAT:
- If a tool was called, your final reply MUST be exactly the tool's `text` content (no prefixes, no explanations). End the response immediately.
- After tool execution, state ONLY the numeric or text result from the tool call result
- Do not explain which tool you used unless asked
- Be concise

BELOW ARE EXAMPLES NOT INSTRUCTIONS

PARAMETER EXTRACTION:
- "add 5 and 4" -> add_numbers(a=5, b=4)
- "what is 10 plus 20" -> add_numbers(a=10, b=20)
- "subtract 3 from 10" -> subtract_numbers(a=10, b=3)
- "20 minus 5" -> subtract_numbers(a=20, b=5)
- "echo hello" -> echo_text(message="hello")
- "say goodbye" -> echo_text(message="goodbye")

COMMON MISTAKES TO AVOID:
- WRONG: Using echo_text for math ("add 5 and 4" -> echo_text)
- RIGHT: Using add_numbers for math ("add 5 and 4" -> add_numbers(a=5, b=4))
- WRONG: Explaining before answering ("I will use the add_numbers tool to...")
- RIGHT: Just return the result from the tool call
- WRONG: Inventing a result before seeing tool output ("The answer is 9")
- RIGHT: Wait for tool result, then report it exactly ("8")

"""


def _create_chat_agent(
    chat_client: Any,
    tools: list[Any] | None,
) -> Agent:
    """Create Agent with standard configuration.

    Args:
        chat_client: The chat client (Azure OpenAI, etc.)
        tools: Optional list of MCP tools

    Returns:
        Configured Agent instance
    """
    return Agent(
        client=chat_client,
        name=AGENT_NAME,
        instructions=AGENT_INSTRUCTIONS,
        tools=tools or None,
        default_options={
            "temperature": 0.0,
            "tool_choice": "auto",
        },
    )


def get_default_config_path() -> Path:
    """Get the default path for MCP server configuration.

    Returns:
        Path to mcp-servers.yaml in the backend directory
    """
    return Path(__file__).parent.parent.parent / "mcp-servers.yaml"


async def create_mcp_tools(config_path: Path | None = None) -> list[MCPStreamableHTTPTool]:
    """Create and connect to all configured MCP servers.

    Loads server configuration from YAML file using MCPServerRegistry.
    Handles individual server failures gracefully - if a server is unavailable,
    it logs a warning and continues with the remaining servers.

    Trace context propagation is handled automatically by the agent-framework
    and FastMCP v3 built-in support.

    Args:
        config_path: Optional path to config file. If None, uses MCP_CONFIG_PATH
                     env var or defaults to mcp-servers.yaml in backend directory.

    Returns:
        List of connected MCPStreamableHTTPTool instances
    """
    with tracer.start_as_current_span("server.create_mcp_tools") as span:
        # Determine config path
        path = config_path
        if path is None and not os.environ.get("MCP_CONFIG_PATH"):
            path = get_default_config_path()

        # Load registry from config
        registry = MCPServerRegistry.load(path)

        # Log loaded configuration
        enabled_servers = registry.get_enabled_servers()
        logger.info(
            "Loaded MCP config: enabled_servers=%d, names=%s",
            len(enabled_servers),
            [s.name for s in enabled_servers],
        )
        span.set_attribute("config.enabled_servers", len(enabled_servers))

        # Get tools from registry
        return await registry.get_all_tools()


def create_agent(
    mcp_tools: list[MCPStreamableHTTPTool] | None = None,
) -> Agent:
    """Create the agent with appropriate chat client based on LLM_PROVIDER.

    Uses LLM_PROVIDER env var to select:
    - 'mock' (default): Agent with MockChatClient for testing
    - 'azure': Agent with AzureOpenAIChatClient

    Both providers return Agent, enabling unified as_mcp_server() support.
    """
    with tracer.start_as_current_span("server.create_agent") as span:
        provider = os.environ.get("LLM_PROVIDER", "mock").lower()
        logger.info("Using LLM provider: %s", provider)
        span.set_attribute("llm.provider", provider)

        tools: list[Any] = list(mcp_tools) if mcp_tools else []
        span.set_attribute("tool_count", len(tools))

        if provider == "mock":
            chat_client = MockChatClient(tools=tools)
            return _create_chat_agent(chat_client, tools)

        # Azure OpenAI
        from agent_framework.azure import AzureOpenAIChatClient
        from azure.identity import AzureCliCredential

        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")

        if not endpoint:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT environment variable is required"
            )
        if not deployment_name:
            raise ValueError(
                "AZURE_OPENAI_DEPLOYMENT_NAME environment variable is required"
            )

        span.set_attribute("azure.deployment", deployment_name)

        chat_client = AzureOpenAIChatClient(
            credential=AzureCliCredential(),
            endpoint=endpoint,
            deployment_name=deployment_name,
        )

        return _create_chat_agent(chat_client, tools)


def create_mcp_asgi(
    mcp_server: Any,
    *,
    stateless: bool = False,
) -> tuple[Starlette, StreamableHTTPSessionManager]:
    """Create an ASGI app from an MCP Server.

    Args:
        mcp_server: The MCP Server instance (from agent.as_mcp_server())
        stateless: Whether to use stateless sessions (default False)

    Returns:
        A tuple of (Starlette app, session_manager)
    """
    session_manager = StreamableHTTPSessionManager(
        app=mcp_server,
        event_store=None,
        json_response=False,
        stateless=stateless,
    )
    asgi_app = StreamableHTTPASGIApp(session_manager)
    starlette_app = Starlette(routes=[Route("/", endpoint=asgi_app)])

    # Instrument for tracing if OTEL is enabled
    if os.environ.get("ENABLE_INSTRUMENTATION", "").lower() == "true":
        StarletteInstrumentor.instrument_app(starlette_app)

    return starlette_app, session_manager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Connect to MCP servers and register agent endpoint at startup."""
    with tracer.start_as_current_span(
        "server.startup",
        attributes={"server.name": "agent-sandbox-server"},
    ) as startup_span:
        try:
            mcp_tools = await create_mcp_tools()
            total = sum(len(t.functions) for t in mcp_tools)
            logger.info(
                "Connected to MCP servers: server_count=%d, tool_count=%d",
                len(mcp_tools),
                total,
            )
            startup_span.set_attribute("mcp.server_count", len(mcp_tools))
            startup_span.set_attribute("mcp.tool_count", total)
        except Exception as e:
            logger.warning(
                "MCP connection failed, running without tools: %s",
                str(e),
            )
            startup_span.set_attribute("mcp.error", str(e))
            startup_span.record_exception(e)
            mcp_tools = []

        agent = create_agent(mcp_tools=mcp_tools or None)

        # Mount AG-UI at /ag-ui (moved from /)
        add_agent_framework_fastapi_endpoint(app, agent, "/ag-ui")
        logger.info("Mounted AG-UI endpoint at /ag-ui")

        # Create and mount MCP server at /mcp
        mcp_server = agent.as_mcp_server(server_name="agent-sandbox")
        mcp_asgi, session_manager = create_mcp_asgi(
            mcp_server, stateless=True
        )
        app.mount("/mcp", mcp_asgi)
        logger.info("Mounted MCP endpoint at /mcp")
        startup_span.set_attribute("startup.complete", True)

    # Run session manager within the app's lifespan
    async with session_manager.run():
        yield


# Create app with lifespan manager
app = FastAPI(title="AG-UI Server", lifespan=lifespan)


class RequestLoggingMiddleware:
    """ASGI middleware that logs requests, including mounted sub-applications."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            method = scope.get("method", "?")
            path = scope.get("path", "?")
            logger.info("Request: %s %s", method, path)
        await self.app(scope, receive, send)


app.add_middleware(RequestLoggingMiddleware)

# Add CORS middleware FIRST (before instrumentation)
# CORS must handle preflight OPTIONS requests before tracing kicks in
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "traceparent", "tracestate"],
    expose_headers=["traceparent", "tracestate"],
)

# Instrument Starlette/FastAPI for tracing AFTER CORS middleware
# This ensures trace context extraction happens on the actual request
if os.environ.get("ENABLE_INSTRUMENTATION", "").lower() == "true":
    StarletteInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)

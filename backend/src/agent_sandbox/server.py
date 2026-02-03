"""AG-UI server for Agent Sandbox."""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework._agents import AgentProtocol
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace

from agent_sandbox.agents.mock_agent import MockAgent
from agent_sandbox.otel_utils import inject_otel_context_to_meta
from agent_sandbox.telemetry import configure_mcp_telemetry, instrument_mcp_app


# Configure OpenTelemetry observability (must be done BEFORE app creation)
# Uses HTTP/protobuf protocol for SigNoz compatibility
if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
    configure_mcp_telemetry("agent-sandbox-server")

    # Enable httpx instrumentation for trace context propagation to MCP servers
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    HTTPXClientInstrumentor().instrument()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TracingMCPTool(MCPStreamableHTTPTool):
    """MCPStreamableHTTPTool subclass that propagates trace context via _meta.

    HTTP headers don't work for MCP trace propagation because the MCP library
    spawns internal async tasks that break OpenTelemetry context. Instead, we
    inject trace context into the _meta field which is passed through the MCP
    JSON-RPC protocol.

    Based on: https://github.com/timvw/fastmcp-otel-langfuse
    """

    async def call_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Override call_tool to inject trace context via _meta field."""
        # Inject current trace context into _meta
        meta = inject_otel_context_to_meta()
        if meta:
            kwargs["_meta"] = meta

        return await super().call_tool(tool_name, **kwargs)


# Multi-server configuration: (name, url) tuples
# Add new servers here - each entry creates an MCPStreamableHTTPTool
MCP_SERVERS: list[tuple[str, str]] = [
    ("text", os.environ.get("MCP_TEXT_URL", "http://localhost:8001/mcp")),
    ("numbers", os.environ.get("MCP_NUMBERS_URL", "http://localhost:8002/mcp")),
]

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
) -> ChatAgent:
    """Create ChatAgent with standard configuration.

    Args:
        chat_client: The chat client (Azure OpenAI, etc.)
        tools: Optional list of MCP tools

    Returns:
        Configured ChatAgent instance
    """
    return ChatAgent(
        name=AGENT_NAME,
        instructions=AGENT_INSTRUCTIONS,
        chat_client=chat_client,
        tools=tools or None,
        default_options={
            "temperature": 0.0,
            "tool_choice": "auto",
        },
    )


async def create_mcp_tools() -> list[TracingMCPTool]:
    """Create and connect to all configured MCP servers.

    Handles individual server failures gracefully - if a server is unavailable,
    it logs a warning and continues with the remaining servers. Retries
    connections to handle startup race conditions.

    Uses TracingMCPTool which injects trace context via _meta field for
    proper distributed tracing across MCP boundaries.
    """
    tools: list[TracingMCPTool] = []
    max_retries = 3
    retry_delay = 1.0

    for name, url in MCP_SERVERS:
        for attempt in range(max_retries):
            try:
                # Create tool with trace context propagation via _meta field
                tool = TracingMCPTool(
                    name=f"{name}-tools",
                    url=url,
                    description=f"Tools provided by the {name} MCP server",
                )
                await tool.connect()
                tools.append(tool)
                logger.info(f"Connected to MCP server '{name}' at {url}")
                break
            except asyncio.CancelledError:
                # Don't retry on cancellation - propagate it
                raise
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.warning(
                        f"MCP server '{name}' unavailable at {url}: {e}")
    return tools


def create_agent(
    mcp_tools: list[TracingMCPTool] | None = None,
) -> AgentProtocol:
    """Create the appropriate agent based on environment configuration.

    Uses LLM_PROVIDER env var to select:
    - 'mock' (default): MockAgent for testing
    - 'azure': ChatAgent with AzureOpenAIChatClient
    """
    provider = os.environ.get("LLM_PROVIDER", "mock").lower()
    logger.info(f"Using LLM provider: {provider}")

    tools: list[Any] = list(mcp_tools) if mcp_tools else []

    if provider == "mock":
        return MockAgent(tools=tools)

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

    chat_client = AzureOpenAIChatClient(
        credential=AzureCliCredential(),
        endpoint=endpoint,
        deployment_name=deployment_name,
    )

    return _create_chat_agent(chat_client, tools)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Connect to MCP servers and register agent endpoint at startup."""
    try:
        mcp_tools = await create_mcp_tools()
        total = sum(len(t.functions) for t in mcp_tools)
        logger.info(
            f"Connected to {len(mcp_tools)} MCP servers, {total} tools")
    except Exception as e:
        logger.warning(f"MCP connection failed: {e}. Running without tools.")
        mcp_tools = []

    agent = create_agent(mcp_tools=mcp_tools or None)
    add_agent_framework_fastapi_endpoint(app, agent, "/")
    yield


# Create app with lifespan manager
app = FastAPI(title="AG-UI Server", lifespan=lifespan)

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
if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
    instrument_mcp_app(app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)

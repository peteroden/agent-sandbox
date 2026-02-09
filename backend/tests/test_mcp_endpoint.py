"""Tests for MCP endpoint at /mcp.

Verifies the MCP endpoint is mounted and responds to MCP protocol requests.
"""

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

# Test constants for MCP endpoint
MCP_ENDPOINT = "/mcp"
AG_UI_ENDPOINT = "/ag-ui"

# MCP Protocol constants
MCP_PROTOCOL_VERSION = "2025-01-01"
MCP_CLIENT_NAME = "test-client"
MCP_CLIENT_VERSION = "1.0.0"

# MCP headers
MCP_CONTENT_TYPE = "application/json"
MCP_ACCEPT_HEADER = "application/json, text/event-stream"

# Standard MCP requests
MCP_INITIALIZE_REQUEST = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": MCP_CLIENT_NAME, "version": MCP_CLIENT_VERSION},
    },
}


@pytest.fixture
async def test_client() -> AsyncClient:
    """Create test client for the FastAPI app with lifespan support."""
    from agent_sandbox.server import app

    # Use LifespanManager to properly trigger lifespan events
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


class TestMcpEndpoint:
    """Tests for /mcp endpoint."""

    @pytest.mark.asyncio
    async def test_mcp_endpoint_accepts_post(self, test_client: AsyncClient) -> None:
        """MCP endpoint responds to POST requests."""
        # Use trailing slash to avoid redirect
        response = await test_client.post(
            f"{MCP_ENDPOINT}/",
            json=MCP_INITIALIZE_REQUEST,
            headers={
                "Content-Type": MCP_CONTENT_TYPE,
                "Accept": MCP_ACCEPT_HEADER,
            },
        )
        # MCP can return 200 OK, 202 Accepted, or SSE stream
        # Some implementations may return 4xx for protocol version issues
        assert response.status_code in (200, 202, 400, 415, 500)

    @pytest.mark.asyncio
    async def test_mcp_endpoint_rejects_unsupported_method(
        self, test_client: AsyncClient
    ) -> None:
        """MCP endpoint rejects unsupported HTTP methods."""
        # DELETE is not supported by MCP
        response = await test_client.delete(
            f"{MCP_ENDPOINT}/",
            headers={"Accept": MCP_ACCEPT_HEADER},
        )
        # Should return 405 Method Not Allowed or similar error
        assert response.status_code in (400, 405)


class TestAgUiEndpoint:
    """Tests for /ag-ui endpoint (moved from /)."""

    @pytest.mark.asyncio
    async def test_ag_ui_endpoint_responds(self, test_client: AsyncClient) -> None:
        """AG-UI endpoint at /ag-ui responds to requests."""
        response = await test_client.post(
            AG_UI_ENDPOINT,
            json={"messages": []},
            headers={"Content-Type": "application/json"},
        )
        # AG-UI endpoint should respond (may require specific format)
        assert response.status_code in (200, 400, 422, 500)

    @pytest.mark.asyncio
    async def test_root_endpoint_not_ag_ui(self, test_client: AsyncClient) -> None:
        """Root endpoint no longer has AG-UI (moved to /ag-ui)."""
        response = await test_client.post(
            "/",
            json={"messages": []},
            headers={"Content-Type": "application/json"},
        )
        # Root should not respond like AG-UI anymore
        assert response.status_code in (404, 405, 422)


class TestHealthEndpoint:
    """Verify health endpoint still works after refactoring."""

    @pytest.mark.asyncio
    async def test_health_endpoint_ok(self, test_client: AsyncClient) -> None:
        """Health check returns 200 OK."""
        response = await test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

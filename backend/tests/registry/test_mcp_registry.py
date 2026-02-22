"""Tests for MCP server registry."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_sandbox.config.mcp_config import MCPRegistryConfig, MCPServerConfig
from tests.conftest import (
    TEST_MCP_SERVER_NAME_NUMBERS,
    TEST_MCP_SERVER_NAME_TEXT,
    TEST_MCP_SERVER_URL_GENERIC,
    TEST_MCP_SERVER_URL_NUMBERS,
    TEST_MCP_SERVER_URL_TEXT,
    TEST_YAML_TWO_SERVERS,
)

# === Local Constants ===
CUSTOM_HEALTH_ENDPOINT = "/healthz"


# === Helpers ===
def create_mock_httpx_client(
    get_handler: AsyncMock | None = None,
    status_code: int = 200,
) -> MagicMock:
    """Create a mock httpx module with configured AsyncClient.

    Args:
        get_handler: Optional custom handler for client.get(). If None, returns
                     a response with the given status_code.
        status_code: Status code for default response (used when get_handler is None).

    Returns:
        Mock httpx module ready for patching.
    """
    mock_httpx = MagicMock()
    mock_client = AsyncMock()

    if get_handler is not None:
        mock_client.get = get_handler
    else:
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_client.get = AsyncMock(return_value=mock_response)

    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()
    mock_httpx.AsyncClient.return_value = mock_client
    return mock_httpx


@pytest.fixture
def two_server_config() -> MCPRegistryConfig:
    """Create a registry config with two enabled servers."""
    return MCPRegistryConfig(
        servers=[
            MCPServerConfig(name=TEST_MCP_SERVER_NAME_TEXT,
                            url=TEST_MCP_SERVER_URL_TEXT),
            MCPServerConfig(name=TEST_MCP_SERVER_NAME_NUMBERS,
                            url=TEST_MCP_SERVER_URL_NUMBERS),
        ]
    )


@pytest.fixture
def mixed_enabled_config() -> MCPRegistryConfig:
    """Create a registry config with one enabled and one disabled server."""
    return MCPRegistryConfig(
        servers=[
            MCPServerConfig(name=TEST_MCP_SERVER_NAME_TEXT,
                            url=TEST_MCP_SERVER_URL_TEXT, enabled=True),
            MCPServerConfig(
                name=TEST_MCP_SERVER_NAME_NUMBERS, url=TEST_MCP_SERVER_URL_NUMBERS, enabled=False
            ),
        ]
    )


@pytest.fixture(autouse=True)
def clear_registry_module_cache() -> None:
    """Clear the registry module from cache before each test.

    This ensures mock patches work correctly by re-importing the module.
    """
    modules_to_remove = [
        key for key in sys.modules if "agent_sandbox.registry" in key
    ]
    for mod in modules_to_remove:
        del sys.modules[mod]


class TestMCPServerRegistry:
    """Tests for MCPServerRegistry class."""

    def test_creates_from_config(self, two_server_config: MCPRegistryConfig) -> None:
        """MCPServerRegistry.from_config creates registry from MCPRegistryConfig."""
        from agent_sandbox.registry.mcp_registry import MCPServerRegistry

        registry = MCPServerRegistry.from_config(two_server_config)

        assert len(registry.servers) == 2
        assert registry.servers[0].name == TEST_MCP_SERVER_NAME_TEXT

    def test_load_from_yaml_path(self, tmp_path: Path) -> None:
        """MCPServerRegistry.load creates registry from YAML file path."""
        config_file = tmp_path / "mcp-servers.yaml"
        config_content = TEST_YAML_TWO_SERVERS.format(
            name1=TEST_MCP_SERVER_NAME_TEXT,
            url1=TEST_MCP_SERVER_URL_TEXT,
            name2=TEST_MCP_SERVER_NAME_NUMBERS,
            url2=TEST_MCP_SERVER_URL_NUMBERS,
            enabled2="true",
        )
        config_file.write_text(config_content)
        from agent_sandbox.registry.mcp_registry import MCPServerRegistry

        registry = MCPServerRegistry.load(config_file)

        assert len(registry.servers) == 2

    def test_load_returns_empty_registry_when_file_missing(self) -> None:
        """MCPServerRegistry.load returns empty registry when file missing."""
        from agent_sandbox.registry.mcp_registry import MCPServerRegistry

        registry = MCPServerRegistry.load(Path("/nonexistent/config.yaml"))

        assert len(registry.servers) == 0

    def test_get_enabled_servers_returns_only_enabled(self) -> None:
        """MCPServerRegistry.get_enabled_servers filters disabled servers."""
        config = MCPRegistryConfig(
            servers=[
                MCPServerConfig(name=TEST_MCP_SERVER_NAME_TEXT,
                                url=TEST_MCP_SERVER_URL_TEXT, enabled=True),
                MCPServerConfig(
                    name=TEST_MCP_SERVER_NAME_NUMBERS, url=TEST_MCP_SERVER_URL_NUMBERS, enabled=False
                ),
                MCPServerConfig(
                    name="other", url="http://localhost:8003/mcp", enabled=True),
            ]
        )

        from agent_sandbox.registry.mcp_registry import MCPServerRegistry

        registry = MCPServerRegistry.from_config(config)
        enabled = registry.get_enabled_servers()

        assert len(enabled) == 2
        assert enabled[0].name == TEST_MCP_SERVER_NAME_TEXT
        assert enabled[1].name == "other"


class TestMCPServerRegistryTools:
    """Tests for MCPServerRegistry tool creation."""

    async def test_get_all_tools_creates_tracing_tools(
        self, two_server_config: MCPRegistryConfig
    ) -> None:
        """get_all_tools returns MCPStreamableHTTPTool instances for enabled servers."""
        mock_tool = MagicMock()
        mock_tool.connect = AsyncMock()
        mock_tool.functions = ["fn1"]

        with patch(
            "agent_sandbox.registry.mcp_registry.MCPStreamableHTTPTool",
            return_value=mock_tool,
        ) as MockTool:
            from agent_sandbox.registry.mcp_registry import MCPServerRegistry

            registry = MCPServerRegistry.from_config(two_server_config)
            tools = await registry.get_all_tools()

            # Should create MCPStreamableHTTPTool for each enabled server
            assert MockTool.call_count == 2
            assert len(tools) == 2

    async def test_get_all_tools_skips_disabled_servers(
        self, mixed_enabled_config: MCPRegistryConfig
    ) -> None:
        """get_all_tools skips disabled servers."""
        mock_tool = MagicMock()
        mock_tool.connect = AsyncMock()
        mock_tool.functions = []

        with patch(
            "agent_sandbox.registry.mcp_registry.MCPStreamableHTTPTool",
            return_value=mock_tool,
        ) as MockTool:
            from agent_sandbox.registry.mcp_registry import MCPServerRegistry

            registry = MCPServerRegistry.from_config(mixed_enabled_config)
            tools = await registry.get_all_tools()

            assert MockTool.call_count == 1
            assert len(tools) == 1

    async def test_get_all_tools_handles_connection_failure(self) -> None:
        """get_all_tools gracefully handles connection failures."""
        config = MCPRegistryConfig(
            servers=[
                MCPServerConfig(
                    name="failing", url=TEST_MCP_SERVER_URL_GENERIC),
                MCPServerConfig(name="working", url=TEST_MCP_SERVER_URL_TEXT),
            ]
        )

        def mock_factory(url: str = "", **kwargs: object) -> MagicMock:
            tool = MagicMock()
            tool.functions = []
            # Server at port 9999 always fails, port 8001 succeeds
            if "9999" in url:
                tool.connect = AsyncMock(side_effect=ConnectionError("Failed"))
            else:
                tool.connect = AsyncMock()
            return tool

        with patch(
            "agent_sandbox.registry.mcp_registry.MCPStreamableHTTPTool",
            side_effect=mock_factory,
        ):
            with patch("agent_sandbox.registry.mcp_registry.asyncio.sleep", new_callable=AsyncMock):
                from agent_sandbox.registry.mcp_registry import MCPServerRegistry

                registry = MCPServerRegistry.from_config(config)
                tools = await registry.get_all_tools()

                # Only one tool should connect successfully
                assert len(tools) == 1


class TestMCPServerRegistryHealthCheck:
    """Tests for MCPServerRegistry health check functionality."""

    async def test_health_check_all_returns_status_dict(
        self, two_server_config: MCPRegistryConfig
    ) -> None:
        """health_check_all returns dict with server name -> health status."""
        from agent_sandbox.registry.mcp_registry import MCPServerRegistry

        registry = MCPServerRegistry.from_config(two_server_config)

        with patch(
            "agent_sandbox.registry.mcp_registry.httpx",
            create_mock_httpx_client(status_code=200),
        ):
            status = await registry.health_check_all()

            assert TEST_MCP_SERVER_NAME_TEXT in status
            assert TEST_MCP_SERVER_NAME_NUMBERS in status
            assert status[TEST_MCP_SERVER_NAME_TEXT] is True
            assert status[TEST_MCP_SERVER_NAME_NUMBERS] is True

    async def test_health_check_all_reports_failures(self) -> None:
        """health_check_all reports False for failed health checks."""
        config = MCPRegistryConfig(
            servers=[
                MCPServerConfig(name="healthy", url=TEST_MCP_SERVER_URL_TEXT),
                MCPServerConfig(name="unhealthy",
                                url=TEST_MCP_SERVER_URL_NUMBERS),
            ]
        )

        from agent_sandbox.registry.mcp_registry import MCPServerRegistry

        registry = MCPServerRegistry.from_config(config)

        async def mock_get(url: str, **kwargs: object) -> MagicMock:
            response = MagicMock()
            if "8001" in url:
                response.status_code = 200
            else:
                response.status_code = 500
            return response

        with patch(
            "agent_sandbox.registry.mcp_registry.httpx",
            create_mock_httpx_client(get_handler=mock_get),
        ):
            status = await registry.health_check_all()

            assert status["healthy"] is True
            assert status["unhealthy"] is False

    async def test_health_check_all_handles_connection_errors(self) -> None:
        """health_check_all reports False for connection errors."""
        config = MCPRegistryConfig(
            servers=[
                MCPServerConfig(name="unreachable",
                                url=TEST_MCP_SERVER_URL_GENERIC),
            ]
        )

        from agent_sandbox.registry.mcp_registry import MCPServerRegistry

        registry = MCPServerRegistry.from_config(config)

        with patch(
            "agent_sandbox.registry.mcp_registry.httpx",
            create_mock_httpx_client(
                get_handler=AsyncMock(
                    side_effect=Exception("Connection refused"))
            ),
        ):
            status = await registry.health_check_all()

            assert status["unreachable"] is False

    async def test_health_check_uses_configured_health_endpoint(self) -> None:
        """health_check_all uses the configured health_endpoint."""
        config = MCPRegistryConfig(
            servers=[
                MCPServerConfig(
                    name="custom",
                    url=TEST_MCP_SERVER_URL_TEXT,
                    health_endpoint=CUSTOM_HEALTH_ENDPOINT,
                ),
            ]
        )

        from agent_sandbox.registry.mcp_registry import MCPServerRegistry

        registry = MCPServerRegistry.from_config(config)

        called_urls: list[str] = []

        async def mock_get(url: str, **kwargs: object) -> MagicMock:
            called_urls.append(url)
            response = MagicMock()
            response.status_code = 200
            return response

        with patch(
            "agent_sandbox.registry.mcp_registry.httpx",
            create_mock_httpx_client(get_handler=mock_get),
        ):
            await registry.health_check_all()

            assert len(called_urls) == 1
            assert CUSTOM_HEALTH_ENDPOINT in called_urls[0]

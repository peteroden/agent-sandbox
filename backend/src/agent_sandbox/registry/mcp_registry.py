"""MCP Server Registry for managing multiple MCP server connections.

This module provides a registry that loads MCP server configuration
from YAML files and creates TracingMCPTool instances for each enabled server.
"""

import asyncio
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from agent_sandbox.config.loader import load_mcp_config
from agent_sandbox.config.mcp_config import MCPRegistryConfig, MCPServerConfig
from agent_sandbox.tools.tracing_mcp_tool import TracingMCPTool

logger = logging.getLogger(__name__)


class MCPServerRegistry:
    """Registry for managing MCP server configurations and connections.

    Supports loading configuration from YAML files, creating TracingMCPTool
    instances for enabled servers, and performing health checks.
    """

    def __init__(self, servers: list[MCPServerConfig]) -> None:
        """Initialize registry with server configurations.

        Args:
            servers: List of MCPServerConfig instances
        """
        self._servers = servers

    @property
    def servers(self) -> list[MCPServerConfig]:
        """Return all configured servers."""
        return self._servers

    @classmethod
    def from_config(cls, config: MCPRegistryConfig) -> "MCPServerRegistry":
        """Create registry from MCPRegistryConfig.

        Args:
            config: Validated configuration object

        Returns:
            MCPServerRegistry instance
        """
        return cls(servers=config.servers)

    @classmethod
    def load(cls, path: Path | None = None) -> "MCPServerRegistry":
        """Load registry from YAML configuration file.

        Args:
            path: Path to YAML config file (uses MCP_CONFIG_PATH env var if None)

        Returns:
            MCPServerRegistry instance (empty if file missing)
        """
        config = load_mcp_config(path)
        return cls.from_config(config)

    def get_enabled_servers(self) -> list[MCPServerConfig]:
        """Return only enabled server configurations.

        Returns:
            List of MCPServerConfig where enabled is True
        """
        return [s for s in self._servers if s.enabled]

    async def get_all_tools(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> list[TracingMCPTool]:
        """Create and connect TracingMCPTool instances for enabled servers.

        Handles individual server failures gracefully - if a server is unavailable,
        it logs a warning and continues with the remaining servers.

        Args:
            max_retries: Maximum connection attempts per server
            retry_delay: Delay between retry attempts in seconds

        Returns:
            List of connected TracingMCPTool instances
        """
        tools: list[TracingMCPTool] = []
        enabled_servers = self.get_enabled_servers()

        for server in enabled_servers:
            for attempt in range(max_retries):
                try:
                    tool = TracingMCPTool(
                        name=f"{server.name}-tools",
                        url=server.url,
                        description=f"Tools provided by the {server.name} MCP server",
                    )
                    await tool.connect()
                    tools.append(tool)
                    logger.info(f"Connected to MCP server '{server.name}' at {server.url}")
                    break
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.debug(
                            f"Retry {attempt + 1}/{max_retries} for '{server.name}': {e}"
                        )
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.warning(
                            f"MCP server '{server.name}' unavailable at {server.url}: {e}"
                        )

        return tools

    async def health_check_all(self, timeout: float = 5.0) -> dict[str, bool]:
        """Check health of all configured servers.

        Performs HTTP GET requests to each server's health endpoint.

        Args:
            timeout: Request timeout in seconds

        Returns:
            Dict mapping server name to health status (True = healthy)
        """
        results: dict[str, bool] = {}

        async with httpx.AsyncClient(timeout=timeout) as client:
            for server in self._servers:
                try:
                    # Build health URL from base URL and health endpoint
                    parsed = urlparse(server.url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    health_url = urljoin(base_url, server.health_endpoint)

                    response = await client.get(health_url)
                    results[server.name] = response.status_code == 200
                except Exception as e:
                    logger.warning(f"Health check failed for '{server.name}': {e}")
                    results[server.name] = False

        return results

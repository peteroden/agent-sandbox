"""MCP Server Registry for managing multiple MCP server connections.

This module provides a registry that loads MCP server configuration
from YAML files and creates TracingMCPTool instances for each enabled server.
"""

import asyncio
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from opentelemetry import trace

from agent_sandbox.config.loader import load_mcp_config
from agent_sandbox.config.mcp_config import MCPRegistryConfig, MCPServerConfig
from agent_sandbox.tools.tracing_mcp_tool import TracingMCPTool

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("agent_sandbox.registry")


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

        with tracer.start_as_current_span(
            "mcp_registry.get_all_tools",
            attributes={"server_count": len(enabled_servers)},
        ) as registry_span:
            for server in enabled_servers:
                with tracer.start_as_current_span(
                    "mcp_registry.connect_server",
                    attributes={
                        "server.name": server.name,
                        "server.url": server.url,
                    },
                ) as server_span:
                    for attempt in range(max_retries):
                        try:
                            tool = TracingMCPTool(
                                name=f"{server.name}-tools",
                                url=server.url,
                                description=f"Tools provided by the {server.name} MCP server",
                            )
                            await tool.connect()
                            tools.append(tool)
                            logger.info(
                                "Connected to MCP server '%s' at %s",
                                server.name,
                                server.url,
                            )
                            server_span.set_attribute("connected", True)
                            server_span.set_attribute("attempts", attempt + 1)
                            break
                        except asyncio.CancelledError:
                            raise
                        except Exception as e:
                            if attempt < max_retries - 1:
                                logger.debug(
                                    "Retry %d/%d for '%s': %s",
                                    attempt + 1,
                                    max_retries,
                                    server.name,
                                    e,
                                )
                                await asyncio.sleep(retry_delay)
                            else:
                                logger.warning(
                                    "MCP server '%s' unavailable at %s: %s",
                                    server.name,
                                    server.url,
                                    e,
                                )
                                server_span.set_attribute("connected", False)
                                server_span.set_attribute("error", str(e))
                                server_span.record_exception(e)

            registry_span.set_attribute("connected_count", len(tools))

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

        with tracer.start_as_current_span(
            "mcp_registry.health_check_all",
            attributes={"server_count": len(self._servers)},
        ) as registry_span:
            async with httpx.AsyncClient(timeout=timeout) as client:
                for server in self._servers:
                    with tracer.start_as_current_span(
                        "mcp_registry.health_check",
                        attributes={"server.name": server.name},
                    ) as server_span:
                        try:
                            # Build health URL from base URL and health endpoint
                            parsed = urlparse(server.url)
                            base_url = f"{parsed.scheme}://{parsed.netloc}"
                            health_url = urljoin(
                                base_url, server.health_endpoint)

                            response = await client.get(health_url)
                            is_healthy = response.status_code == 200
                            results[server.name] = is_healthy
                            server_span.set_attribute("healthy", is_healthy)
                            server_span.set_attribute(
                                "status_code", response.status_code)
                        except Exception as e:
                            logger.warning(
                                "Health check failed for '%s': %s",
                                server.name,
                                e,
                            )
                            results[server.name] = False
                            server_span.set_attribute("healthy", False)
                            server_span.set_attribute("error", str(e))
                            server_span.record_exception(e)

            healthy_count = sum(1 for v in results.values() if v)
            registry_span.set_attribute("healthy_count", healthy_count)

        return results

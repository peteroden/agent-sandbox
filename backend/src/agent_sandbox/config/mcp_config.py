"""Pydantic models for MCP server configuration.

This module defines the configuration schema for the MCP server registry,
supporting YAML-based configuration with environment variable interpolation.
"""

from pydantic import BaseModel, Field, field_validator


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server.

    Attributes:
        name: Unique identifier for the server
        url: Full URL including path (e.g., http://localhost:8001/mcp)
        enabled: Whether the server should be used (default: True)
        health_endpoint: Path for health checks (default: /health)
    """

    name: str = Field(..., min_length=1, description="Unique server identifier")
    url: str = Field(..., description="Server URL with MCP path")
    enabled: bool = Field(default=True, description="Whether server is enabled")
    health_endpoint: str = Field(default="/health", description="Health check path")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL has proper format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class MCPRegistryConfig(BaseModel):
    """Configuration for the MCP server registry.

    Attributes:
        servers: List of MCP server configurations
    """

    servers: list[MCPServerConfig] = Field(
        default_factory=list, description="List of MCP servers"
    )

    def get_enabled_servers(self) -> list[MCPServerConfig]:
        """Return only enabled servers.

        Returns:
            List of MCPServerConfig instances where enabled is True
        """
        return [s for s in self.servers if s.enabled]

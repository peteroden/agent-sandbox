"""Tests for MCP configuration models."""

import pytest
from pydantic import ValidationError

from tests.conftest import (
    TEST_MCP_SERVER_NAME_NUMBERS,
    TEST_MCP_SERVER_NAME_TEXT,
    TEST_MCP_SERVER_URL_NUMBERS,
    TEST_MCP_SERVER_URL_TEXT,
)

# === Local Constants ===
DEFAULT_HEALTH_ENDPOINT = "/health"
CUSTOM_HEALTH_ENDPOINT = "/healthz"


class TestMCPServerConfig:
    """Tests for MCPServerConfig Pydantic model."""

    def test_valid_config_with_required_fields(self) -> None:
        """MCPServerConfig accepts valid config with required fields."""
        from agent_sandbox.config.mcp_config import MCPServerConfig

        config = MCPServerConfig(
            name=TEST_MCP_SERVER_NAME_TEXT, url=TEST_MCP_SERVER_URL_TEXT)

        assert config.name == TEST_MCP_SERVER_NAME_TEXT
        assert config.url == TEST_MCP_SERVER_URL_TEXT

    def test_default_enabled_is_true(self) -> None:
        """MCPServerConfig defaults enabled to True."""
        from agent_sandbox.config.mcp_config import MCPServerConfig

        config = MCPServerConfig(
            name=TEST_MCP_SERVER_NAME_TEXT, url=TEST_MCP_SERVER_URL_TEXT)

        assert config.enabled is True

    def test_default_health_endpoint(self) -> None:
        """MCPServerConfig defaults health_endpoint to /health."""
        from agent_sandbox.config.mcp_config import MCPServerConfig

        config = MCPServerConfig(
            name=TEST_MCP_SERVER_NAME_TEXT, url=TEST_MCP_SERVER_URL_TEXT)

        assert config.health_endpoint == DEFAULT_HEALTH_ENDPOINT

    def test_all_fields_can_be_set(self) -> None:
        """MCPServerConfig allows setting all fields explicitly."""
        from agent_sandbox.config.mcp_config import MCPServerConfig

        config = MCPServerConfig(
            name=TEST_MCP_SERVER_NAME_NUMBERS,
            url=TEST_MCP_SERVER_URL_NUMBERS,
            enabled=False,
            health_endpoint=CUSTOM_HEALTH_ENDPOINT,
        )

        assert config.name == TEST_MCP_SERVER_NAME_NUMBERS
        assert config.url == TEST_MCP_SERVER_URL_NUMBERS
        assert config.enabled is False
        assert config.health_endpoint == CUSTOM_HEALTH_ENDPOINT

    @pytest.mark.parametrize(
        ("config_kwargs", "error_field"),
        [
            ({"url": TEST_MCP_SERVER_URL_TEXT}, "name"),
            ({"name": TEST_MCP_SERVER_NAME_TEXT}, "url"),
            ({"name": "", "url": TEST_MCP_SERVER_URL_TEXT}, "name"),
        ],
        ids=["missing-name", "missing-url", "empty-name"],
    )
    def test_rejects_invalid_config(self, config_kwargs: dict[str, str], error_field: str) -> None:
        """MCPServerConfig rejects config without required fields or empty values."""
        from agent_sandbox.config.mcp_config import MCPServerConfig

        with pytest.raises(ValidationError) as exc_info:
            MCPServerConfig(**config_kwargs)  # type: ignore

        assert error_field in str(exc_info.value)

    def test_rejects_invalid_url(self) -> None:
        """MCPServerConfig rejects invalid URL format."""
        from agent_sandbox.config.mcp_config import MCPServerConfig

        with pytest.raises(ValidationError):
            MCPServerConfig(name=TEST_MCP_SERVER_NAME_TEXT,
                            url="not-a-valid-url")


class TestMCPRegistryConfig:
    """Tests for MCPRegistryConfig Pydantic model."""

    def test_valid_registry_with_servers(self) -> None:
        """MCPRegistryConfig accepts valid config with servers list."""
        from agent_sandbox.config.mcp_config import MCPRegistryConfig, MCPServerConfig

        config = MCPRegistryConfig(
            servers=[
                MCPServerConfig(name=TEST_MCP_SERVER_NAME_TEXT,
                                url=TEST_MCP_SERVER_URL_TEXT),
                MCPServerConfig(name=TEST_MCP_SERVER_NAME_NUMBERS,
                                url=TEST_MCP_SERVER_URL_NUMBERS),
            ]
        )

        assert len(config.servers) == 2
        assert config.servers[0].name == TEST_MCP_SERVER_NAME_TEXT
        assert config.servers[1].name == TEST_MCP_SERVER_NAME_NUMBERS

    def test_empty_servers_list_allowed(self) -> None:
        """MCPRegistryConfig allows empty servers list."""
        from agent_sandbox.config.mcp_config import MCPRegistryConfig

        config = MCPRegistryConfig(servers=[])

        assert config.servers == []

    def test_from_dict_creates_valid_config(self) -> None:
        """MCPRegistryConfig can be created from dictionary (simulating YAML parse)."""
        from agent_sandbox.config.mcp_config import MCPRegistryConfig

        data = {
            "servers": [
                {"name": TEST_MCP_SERVER_NAME_TEXT,
                    "url": TEST_MCP_SERVER_URL_TEXT},
                {"name": TEST_MCP_SERVER_NAME_NUMBERS,
                    "url": TEST_MCP_SERVER_URL_NUMBERS, "enabled": False},
            ]
        }

        config = MCPRegistryConfig.model_validate(data)

        assert len(config.servers) == 2
        assert config.servers[0].enabled is True
        assert config.servers[1].enabled is False

    def test_rejects_invalid_server_in_list(self) -> None:
        """MCPRegistryConfig rejects invalid server config in list."""
        from agent_sandbox.config.mcp_config import MCPRegistryConfig

        data = {
            "servers": [
                {"name": TEST_MCP_SERVER_NAME_TEXT},  # Missing url
            ]
        }

        with pytest.raises(ValidationError):
            MCPRegistryConfig.model_validate(data)

    def test_get_enabled_servers(self) -> None:
        """MCPRegistryConfig.get_enabled_servers returns only enabled servers."""
        from agent_sandbox.config.mcp_config import MCPRegistryConfig, MCPServerConfig

        config = MCPRegistryConfig(
            servers=[
                MCPServerConfig(name=TEST_MCP_SERVER_NAME_TEXT,
                                url=TEST_MCP_SERVER_URL_TEXT, enabled=True),
                MCPServerConfig(name=TEST_MCP_SERVER_NAME_NUMBERS,
                                url=TEST_MCP_SERVER_URL_NUMBERS, enabled=False),
                MCPServerConfig(
                    name="other", url="http://localhost:8003/mcp", enabled=True),
            ]
        )

        enabled = config.get_enabled_servers()

        assert len(enabled) == 2
        assert enabled[0].name == TEST_MCP_SERVER_NAME_TEXT
        assert enabled[1].name == "other"

"""Tests for server module."""

import logging
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import (
    ENV_AZURE_DEPLOYMENT,
    ENV_AZURE_ENDPOINT,
    ENV_LLM_PROVIDER,
    LLM_PROVIDER_AZURE,
    LLM_PROVIDER_MOCK,
    TEST_AZURE_DEPLOYMENT,
    TEST_AZURE_ENDPOINT,
    TEST_MCP_SERVER_NAME_TEXT,
    TEST_MCP_SERVER_URL_GENERIC,
)

# Expected agent type for both providers (unified)
EXPECTED_AGENT_TYPE = "Agent"

# === Local Constants ===
YAML_SINGLE_SERVER = """
servers:
  - name: {name}
    url: {url}
    enabled: {enabled}
"""


class TestCreateAgentProviderSelection:
    """Tests for create_agent LLM provider selection."""

    @pytest.mark.parametrize(
        "provider",
        [
            LLM_PROVIDER_MOCK,
            LLM_PROVIDER_AZURE,
        ],
    )
    def test_create_agent_returns_chat_agent_for_all_providers(
        self, provider: str
    ) -> None:
        """create_agent returns Agent for all providers."""
        env = {ENV_LLM_PROVIDER: provider}
        if provider == LLM_PROVIDER_AZURE:
            env[ENV_AZURE_ENDPOINT] = TEST_AZURE_ENDPOINT
            env[ENV_AZURE_DEPLOYMENT] = TEST_AZURE_DEPLOYMENT

        patches = []
        if provider == LLM_PROVIDER_AZURE:
            patches.append(
                patch("agent_framework.azure.AzureOpenAIChatClient", MagicMock())
            )

        with patch.dict(os.environ, env, clear=False):
            for p in patches:
                p.start()
            try:
                from agent_sandbox.server import create_agent

                agent = create_agent()
                assert type(agent).__name__ == EXPECTED_AGENT_TYPE
            finally:
                for p in patches:
                    p.stop()

    def test_create_agent_defaults_to_mock_provider(self) -> None:
        """create_agent uses MockChatClient when LLM_PROVIDER is unset."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_LLM_PROVIDER, None)
            from agent_sandbox.server import create_agent
            from agent_sandbox.agents.mock_chat_client import MockChatClient

            agent = create_agent()
            assert type(agent).__name__ == EXPECTED_AGENT_TYPE
            assert isinstance(agent.client, MockChatClient)


class TestCreateAgentUnified:
    """Tests for unified Agent creation."""

    def test_mock_provider_uses_mock_chat_client(self) -> None:
        """Mock provider creates Agent with MockChatClient."""
        with patch.dict(os.environ, {ENV_LLM_PROVIDER: LLM_PROVIDER_MOCK}):
            from agent_sandbox.server import create_agent
            from agent_sandbox.agents.mock_chat_client import MockChatClient

            agent = create_agent()
            assert isinstance(agent.client, MockChatClient)

    def test_azure_provider_uses_azure_chat_client(self) -> None:
        """Azure provider creates Agent with AzureOpenAIChatClient."""
        env = {
            ENV_LLM_PROVIDER: LLM_PROVIDER_AZURE,
            ENV_AZURE_ENDPOINT: TEST_AZURE_ENDPOINT,
            ENV_AZURE_DEPLOYMENT: TEST_AZURE_DEPLOYMENT,
        }

        with patch.dict(os.environ, env, clear=False):
            with patch("agent_framework.azure.AzureOpenAIChatClient") as MockClient:
                mock_client_instance = MagicMock()
                MockClient.return_value = mock_client_instance

                from agent_sandbox.server import create_agent

                agent = create_agent()
                assert agent.client is mock_client_instance

    def test_agent_has_as_mcp_server_method(self) -> None:
        """Agent has as_mcp_server() method."""
        with patch.dict(os.environ, {ENV_LLM_PROVIDER: LLM_PROVIDER_MOCK}):
            from agent_sandbox.server import create_agent

            agent = create_agent()
            assert hasattr(agent, "as_mcp_server")
            assert callable(agent.as_mcp_server)


class TestCreateAgentAzureValidation:
    """Tests for Azure provider validation."""

    @pytest.mark.parametrize(
        ("missing_var", "error_match"),
        [
            (ENV_AZURE_ENDPOINT, ENV_AZURE_ENDPOINT),
            (ENV_AZURE_DEPLOYMENT, ENV_AZURE_DEPLOYMENT),
        ],
    )
    def test_azure_provider_requires_config(
        self, missing_var: str, error_match: str
    ) -> None:
        """Azure provider raises ValueError when required config is missing."""
        env = {
            ENV_LLM_PROVIDER: LLM_PROVIDER_AZURE,
            ENV_AZURE_ENDPOINT: TEST_AZURE_ENDPOINT,
            ENV_AZURE_DEPLOYMENT: TEST_AZURE_DEPLOYMENT,
        }
        env.pop(missing_var)

        with patch.dict(os.environ, env, clear=False):
            os.environ.pop(missing_var, None)
            from agent_sandbox.server import create_agent

            with pytest.raises(ValueError, match=error_match):
                create_agent()


class TestCreateAgentWithTools:
    """Tests for create_agent with MCP tools."""

    def test_create_agent_passes_tools_to_agent(self) -> None:
        """MCP tools are passed to the agent."""
        mock_tools = [MagicMock(), MagicMock()]

        with patch.dict(os.environ, {ENV_LLM_PROVIDER: LLM_PROVIDER_MOCK}):
            from agent_sandbox.server import create_agent

            agent = create_agent(mcp_tools=mock_tools)  # type: ignore

            # Agent normalizes tools; verify count matches
            assert len(agent.default_options["tools"]) == len(mock_tools)

    def test_create_agent_works_without_tools(self) -> None:
        """Agent works with no tools."""
        with patch.dict(os.environ, {ENV_LLM_PROVIDER: LLM_PROVIDER_MOCK}):
            from agent_sandbox.server import create_agent

            agent = create_agent(mcp_tools=None)

            # Agent stores tools in default_options (empty list when None)
            assert agent.default_options["tools"] == []


class TestCreateAgentHelper:
    """Tests for _create_chat_agent helper function."""

    def test_create_chat_agent_returns_agent_with_expected_name(self) -> None:
        """_create_chat_agent sets the agent name from AGENT_NAME constant."""
        mock_client = MagicMock()

        from agent_sandbox.server import AGENT_NAME, _create_chat_agent

        agent = _create_chat_agent(mock_client, tools=None)

        assert agent.name == AGENT_NAME

    def test_create_chat_agent_sets_instructions(self) -> None:
        """_create_chat_agent sets instructions from AGENT_INSTRUCTIONS constant."""
        mock_client = MagicMock()

        from agent_sandbox.server import AGENT_INSTRUCTIONS, _create_chat_agent

        agent = _create_chat_agent(mock_client, tools=None)

        # Instructions are stored in default_options dict
        assert agent.default_options["instructions"] == AGENT_INSTRUCTIONS

    def test_create_chat_agent_passes_tools(self) -> None:
        """_create_chat_agent passes tools to the Agent."""
        mock_client = MagicMock()
        mock_tools = [MagicMock(), MagicMock()]

        from agent_sandbox.server import _create_chat_agent

        agent = _create_chat_agent(mock_client, tools=mock_tools)

        # Agent normalizes tools; verify count matches
        assert len(agent.default_options["tools"]) == len(mock_tools)

    def test_create_chat_agent_handles_empty_tools(self) -> None:
        """_create_chat_agent handles empty tools list."""
        mock_client = MagicMock()

        from agent_sandbox.server import _create_chat_agent

        agent = _create_chat_agent(mock_client, tools=[])

        # Empty tools list is converted to None by our helper, Agent stores as []
        assert agent.default_options["tools"] == []


class TestAgentInstructions:
    """Tests for AGENT_INSTRUCTIONS content."""

    def test_agent_instructions_contains_decision_process(self) -> None:
        """AGENT_INSTRUCTIONS includes decision process for tool selection."""
        from agent_sandbox.server import AGENT_INSTRUCTIONS

        # Must contain decision tree structure
        assert "decision process" in AGENT_INSTRUCTIONS.lower()
        assert "parameter extraction" in AGENT_INSTRUCTIONS.lower()

    def test_agent_instructions_mentions_tool_execution(self) -> None:
        """AGENT_INSTRUCTIONS includes guidance for tool execution."""
        from agent_sandbox.server import AGENT_INSTRUCTIONS

        assert "tool" in AGENT_INSTRUCTIONS.lower()

    def test_agent_instructions_mentions_returning_results(self) -> None:
        """AGENT_INSTRUCTIONS includes guidance for returning tool results."""
        from agent_sandbox.server import AGENT_INSTRUCTIONS

        assert "result" in AGENT_INSTRUCTIONS.lower()

    def test_agent_instructions_contains_mistakes_to_avoid(self) -> None:
        """AGENT_INSTRUCTIONS includes common mistakes to avoid."""
        from agent_sandbox.server import AGENT_INSTRUCTIONS

        assert "mistakes to avoid" in AGENT_INSTRUCTIONS.lower()
        assert "wrong" in AGENT_INSTRUCTIONS.lower()
        assert "right" in AGENT_INSTRUCTIONS.lower()


class TestCreateMCPTools:
    """Tests for create_mcp_tools graceful degradation."""

    async def test_create_mcp_tools_handles_connection_failures(
        self, clear_server_module_cache: None
    ) -> None:
        """create_mcp_tools continues when one server fails after retries."""
        def mock_factory(url: str = "", **_: object) -> MagicMock:
            tool = MagicMock()
            tool.functions = []
            # First server always fails, second always succeeds
            if "8001" in url:
                tool.connect = AsyncMock(side_effect=ConnectionError())
            else:
                tool.connect = AsyncMock()
            return tool

        with patch("agent_sandbox.registry.mcp_registry.MCPStreamableHTTPTool", side_effect=mock_factory):
            with patch("agent_sandbox.registry.mcp_registry.asyncio.sleep", new_callable=AsyncMock):
                from agent_sandbox.server import create_mcp_tools

                tools = await create_mcp_tools()

        assert len(tools) == 1  # Only one server connected

    async def test_create_mcp_tools_returns_empty_when_all_fail(
        self, clear_server_module_cache: None
    ) -> None:
        """create_mcp_tools returns empty list when all servers fail."""
        with patch("agent_sandbox.registry.mcp_registry.MCPStreamableHTTPTool") as MockTool:
            mock = MagicMock()
            mock.connect = AsyncMock(side_effect=ConnectionError())
            MockTool.return_value = mock

            with patch("agent_sandbox.registry.mcp_registry.asyncio.sleep", new_callable=AsyncMock):
                from agent_sandbox.server import create_mcp_tools

                tools = await create_mcp_tools()

            assert tools == []


class TestMCPRegistryIntegration:
    """Tests for MCP registry integration in server."""

    def test_get_default_config_path_returns_mcp_servers_yaml(
        self, clear_server_module_cache: None
    ) -> None:
        """get_default_config_path returns path to mcp-servers.yaml."""
        from agent_sandbox.server import get_default_config_path

        config_path = get_default_config_path()

        assert config_path.name == "mcp-servers.yaml"
        assert config_path.exists()

    async def test_create_mcp_tools_uses_registry(
        self, tmp_path: Path, clear_server_module_cache: None
    ) -> None:
        """create_mcp_tools uses MCPServerRegistry to load config."""
        config_file = tmp_path / "test-mcp.yaml"
        config_content = YAML_SINGLE_SERVER.format(
            name=TEST_MCP_SERVER_NAME_TEXT,
            url=TEST_MCP_SERVER_URL_GENERIC,
            enabled="true",
        )
        config_file.write_text(config_content)
        mock_tool = MagicMock()
        mock_tool.connect = AsyncMock()
        mock_tool.functions = []

        with patch.dict(os.environ, {"MCP_CONFIG_PATH": str(config_file)}):
            with patch("agent_sandbox.registry.mcp_registry.MCPStreamableHTTPTool", return_value=mock_tool):
                from agent_sandbox.server import create_mcp_tools

                tools = await create_mcp_tools()

                # Should have loaded from our test config
                assert len(tools) == 1

    async def test_create_mcp_tools_logs_config_at_startup(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture, clear_server_module_cache: None
    ) -> None:
        """create_mcp_tools logs loaded configuration."""
        logged_server_name = "logged-server"
        config_file = tmp_path / "test-mcp.yaml"
        config_content = YAML_SINGLE_SERVER.format(
            name=logged_server_name,
            url=TEST_MCP_SERVER_URL_GENERIC,
            enabled="true",
        )
        config_file.write_text(config_content)
        mock_tool = MagicMock()
        mock_tool.connect = AsyncMock()
        mock_tool.functions = []

        with caplog.at_level(logging.INFO):
            with patch.dict(os.environ, {"MCP_CONFIG_PATH": str(config_file)}):
                with patch("agent_sandbox.registry.mcp_registry.MCPStreamableHTTPTool", return_value=mock_tool):
                    from agent_sandbox.server import create_mcp_tools

                    await create_mcp_tools()

        # Should log server connection
        assert any(
            logged_server_name in record.message for record in caplog.records)

"""Tests for server module."""

import os
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
)


class TestCreateAgentProviderSelection:
    """Tests for create_agent LLM provider selection."""

    @pytest.mark.parametrize(
        ("provider", "expected_agent"),
        [
            (LLM_PROVIDER_MOCK, "MockAgent"),
            (LLM_PROVIDER_AZURE, "ChatAgent"),
        ],
    )
    def test_create_agent_selects_correct_agent_type(
        self, provider: str, expected_agent: str
    ) -> None:
        """create_agent returns correct agent type based on LLM_PROVIDER."""
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
                assert type(agent).__name__ == expected_agent
            finally:
                for p in patches:
                    p.stop()

    def test_create_agent_defaults_to_mock(self) -> None:
        """create_agent uses mock when LLM_PROVIDER is unset."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_LLM_PROVIDER, None)
            from agent_sandbox.server import create_agent

            agent = create_agent()
            assert type(agent).__name__ == "MockAgent"


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

            assert agent.tools == mock_tools

    def test_create_agent_works_without_tools(self) -> None:
        """Agent works with no tools."""
        with patch.dict(os.environ, {ENV_LLM_PROVIDER: LLM_PROVIDER_MOCK}):
            from agent_sandbox.server import create_agent

            agent = create_agent(mcp_tools=None)

            assert agent.tools == []


class TestCreateChatAgentHelper:
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
        """_create_chat_agent passes tools to the ChatAgent."""
        mock_client = MagicMock()
        mock_tools = [MagicMock(), MagicMock()]

        from agent_sandbox.server import _create_chat_agent

        agent = _create_chat_agent(mock_client, tools=mock_tools)

        # Tools are stored in default_options dict
        assert agent.default_options["tools"] == mock_tools

    def test_create_chat_agent_handles_empty_tools(self) -> None:
        """_create_chat_agent handles empty tools list."""
        mock_client = MagicMock()

        from agent_sandbox.server import _create_chat_agent

        agent = _create_chat_agent(mock_client, tools=[])

        # Empty tools list is converted to None by our helper, ChatAgent stores as []
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

    async def test_create_mcp_tools_handles_connection_failures(self) -> None:
        """create_mcp_tools continues when one server fails after retries."""
        server_urls_seen: list[str] = []

        def mock_factory(url: str = "", **_: object) -> MagicMock:
            server_urls_seen.append(url)
            tool = MagicMock()
            # First server always fails, second always succeeds
            if "8001" in url:
                tool.connect = AsyncMock(side_effect=ConnectionError())
            else:
                tool.connect = AsyncMock()
            return tool

        with patch("agent_sandbox.server.TracingMCPTool", side_effect=mock_factory):
            with patch("agent_sandbox.server.asyncio.sleep", new_callable=AsyncMock):
                from agent_sandbox.server import create_mcp_tools

                tools = await create_mcp_tools()

        assert len(tools) == 1  # Only one server connected

    async def test_create_mcp_tools_returns_empty_when_all_fail(self) -> None:
        """create_mcp_tools returns empty list when all servers fail."""
        with patch("agent_sandbox.server.TracingMCPTool") as MockTool:
            mock = MagicMock()
            mock.connect = AsyncMock(side_effect=ConnectionError())
            MockTool.return_value = mock

            with patch("agent_sandbox.server.asyncio.sleep", new_callable=AsyncMock):
                from agent_sandbox.server import create_mcp_tools

                tools = await create_mcp_tools()

            assert tools == []

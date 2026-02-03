"""Pytest configuration for backend tests."""

import os
import sys
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# === Test Constants ===

# LLM Providers
LLM_PROVIDER_MOCK = "mock"
LLM_PROVIDER_AZURE = "azure"

# Environment variable names
ENV_LLM_PROVIDER = "LLM_PROVIDER"
ENV_AZURE_ENDPOINT = "AZURE_OPENAI_ENDPOINT"
ENV_AZURE_DEPLOYMENT = "AZURE_OPENAI_DEPLOYMENT_NAME"

# Test Azure values
TEST_AZURE_ENDPOINT = "https://test.openai.azure.com/"
TEST_AZURE_DEPLOYMENT = "gpt-4"

# Test service values
TEST_SERVICE_NAME = "test"
TEST_SERVICE_URL = "http://localhost:8000"


@pytest.fixture(autouse=True)
def mock_server_init() -> Generator[None]:
    """Mock server module initialization before import.

    This prevents MCP connections during tests.
    """
    # Remove cached module if already imported
    modules_to_remove = [
        key for key in sys.modules if key.startswith("agent_sandbox.server")
    ]
    for mod in modules_to_remove:
        del sys.modules[mod]

    # Mock MCPStreamableHTTPTool before server module import
    mock_tool = MagicMock()
    mock_tool.connect = AsyncMock()
    mock_tool.functions = []

    # Ensure tests use mock agent by default
    original_env = os.environ.copy()
    os.environ[ENV_LLM_PROVIDER] = LLM_PROVIDER_MOCK

    with patch(
        "agent_framework.MCPStreamableHTTPTool",
        return_value=mock_tool,
    ):
        yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

    # Clean up after test
    modules_to_remove = [
        key for key in sys.modules if key.startswith("agent_sandbox.server")
    ]
    for mod in modules_to_remove:
        del sys.modules[mod]

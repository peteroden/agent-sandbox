"""Pytest configuration for backend tests.

Only constants used in 2+ test files belong here.
Single-use constants should be local to their test file.
"""

import os
import sys
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# === Shared Constants (used in 2+ files) ===

# LLM Providers (used in fixtures)
LLM_PROVIDER_MOCK = "mock"
LLM_PROVIDER_AZURE = "azure"

# Environment variable names (used in fixtures)
ENV_LLM_PROVIDER = "LLM_PROVIDER"
ENV_AZURE_ENDPOINT = "AZURE_OPENAI_ENDPOINT"
ENV_AZURE_DEPLOYMENT = "AZURE_OPENAI_DEPLOYMENT_NAME"

# Test Azure values (used in fixtures)
TEST_AZURE_ENDPOINT = "https://test.openai.azure.com/"
TEST_AZURE_DEPLOYMENT = "gpt-4"

# Test service values (used in test_health.py, test_telemetry.py)
TEST_SERVICE_NAME = "test"
TEST_SERVICE_URL = "http://localhost:8000"

# MCP Server Constants (used in config, loader, registry tests)
TEST_MCP_SERVER_NAME_TEXT = "text"
TEST_MCP_SERVER_NAME_NUMBERS = "numbers"
TEST_MCP_SERVER_URL_TEXT = "http://localhost:8001/mcp"
TEST_MCP_SERVER_URL_NUMBERS = "http://localhost:8002/mcp"
TEST_MCP_SERVER_URL_GENERIC = "http://localhost:9999/mcp"

# YAML Templates (used in loader, registry tests)
TEST_YAML_TWO_SERVERS = """
servers:
  - name: {name1}
    url: {url1}
  - name: {name2}
    url: {url2}
    enabled: {enabled2}
"""

# Env value lists for parameterized tests
TRUTHY_ENV_VALUES = ["true", "1", "yes", "TRUE", "Yes"]
FALSY_ENV_VALUES = ["false", "0", "no", ""]


@pytest.fixture
def clear_server_module_cache() -> None:
    """Clear server and registry modules from cache.

    This ensures mock patches work correctly by re-importing the module.
    """
    modules_to_remove = [
        key for key in sys.modules
        if "agent_sandbox.server" in key or "agent_sandbox.registry" in key
    ]
    for mod in modules_to_remove:
        del sys.modules[mod]


@pytest.fixture
def clear_registry_module_cache() -> None:
    """Clear the registry module from cache before each test.

    This ensures mock patches work correctly by re-importing the module.
    """
    modules_to_remove = [
        key for key in sys.modules if "agent_sandbox.registry" in key
    ]
    for mod in modules_to_remove:
        del sys.modules[mod]


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

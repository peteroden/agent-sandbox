"""Tests for MCP configuration loader."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import pytest

from tests.conftest import (
    TEST_MCP_SERVER_NAME_NUMBERS,
    TEST_MCP_SERVER_NAME_TEXT,
    TEST_MCP_SERVER_URL_NUMBERS,
    TEST_MCP_SERVER_URL_TEXT,
    TEST_YAML_TWO_SERVERS,
)


def _make_yaml_content(
    name: str,
    url: str,
    enabled: bool = True,
    name2: str | None = None,
    url2: str | None = None,
    enabled2: bool = True,
) -> str:
    """Generate YAML content for test config files."""
    if name2 and url2:
        return TEST_YAML_TWO_SERVERS.format(
            name1=name,
            url1=url,
            name2=name2,
            url2=url2,
            enabled2="true" if enabled2 else "false",
        )
    return f"""
servers:
  - name: {name}
    url: {url}
    enabled: {"true" if enabled else "false"}
"""


class TestLoadMCPConfig:
    """Tests for load_mcp_config function."""

    def test_loads_valid_yaml_file(self, tmp_path: Path) -> None:
        """load_mcp_config parses valid YAML file."""
        config_file = tmp_path / "mcp-servers.yaml"
        config_content = _make_yaml_content(
            name=TEST_MCP_SERVER_NAME_TEXT,
            url=TEST_MCP_SERVER_URL_TEXT,
            name2=TEST_MCP_SERVER_NAME_NUMBERS,
            url2=TEST_MCP_SERVER_URL_NUMBERS,
            enabled2=False,
        )
        config_file.write_text(config_content)
        from agent_sandbox.config.loader import load_mcp_config

        config = load_mcp_config(config_file)

        assert len(config.servers) == 2
        assert config.servers[0].name == TEST_MCP_SERVER_NAME_TEXT
        assert config.servers[1].enabled is False

    def test_returns_empty_config_when_file_missing(self) -> None:
        """load_mcp_config returns empty config when file doesn't exist."""
        from agent_sandbox.config.loader import load_mcp_config

        config = load_mcp_config(Path("/nonexistent/path/config.yaml"))

        assert config.servers == []

    def test_interpolates_env_var_simple(self, tmp_path: Path) -> None:
        """load_mcp_config interpolates ${VAR} with env value."""
        config_file = tmp_path / "mcp-servers.yaml"
        config_file.write_text(f"""
servers:
  - name: {TEST_MCP_SERVER_NAME_TEXT}
    url: ${{TEST_MCP_URL}}
""")
        test_url = "http://test:9000/mcp"
        with patch.dict(os.environ, {"TEST_MCP_URL": test_url}):
            from agent_sandbox.config.loader import load_mcp_config

            config = load_mcp_config(config_file)

        assert config.servers[0].url == test_url

    def test_interpolates_env_var_with_default(self, tmp_path: Path) -> None:
        """load_mcp_config interpolates ${VAR:-default} using default when VAR unset."""
        config_file = tmp_path / "mcp-servers.yaml"
        fallback_url = "http://fallback:8001/mcp"
        config_file.write_text(f"""
servers:
  - name: {TEST_MCP_SERVER_NAME_TEXT}
    url: ${{UNSET_VAR:-{fallback_url}}}
""")
        # Ensure variable is unset
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("UNSET_VAR", None)
            from agent_sandbox.config.loader import load_mcp_config

            config = load_mcp_config(config_file)

        assert config.servers[0].url == fallback_url

    def test_env_var_overrides_default(self, tmp_path: Path) -> None:
        """load_mcp_config uses env value when set, ignoring default."""
        config_file = tmp_path / "mcp-servers.yaml"
        config_file.write_text(f"""
servers:
  - name: {TEST_MCP_SERVER_NAME_TEXT}
    url: ${{MY_URL:-http://default/mcp}}
""")
        override_url = "http://override:1234/mcp"
        with patch.dict(os.environ, {"MY_URL": override_url}):
            from agent_sandbox.config.loader import load_mcp_config

            config = load_mcp_config(config_file)

        assert config.servers[0].url == override_url

    def test_uses_mcp_config_path_env_var(self, tmp_path: Path) -> None:
        """load_mcp_config uses MCP_CONFIG_PATH env var when path is None."""
        config_file = tmp_path / "mcp-servers.yaml"
        config_url = "http://from-env/mcp"
        config_content = _make_yaml_content(
            name=TEST_MCP_SERVER_NAME_TEXT, url=config_url)
        config_file.write_text(config_content)
        with patch.dict(os.environ, {"MCP_CONFIG_PATH": str(config_file)}):
            from agent_sandbox.config.loader import load_mcp_config

            config = load_mcp_config(None)

        assert config.servers[0].url == config_url

    def test_explicit_path_overrides_env_var(self, tmp_path: Path) -> None:
        """load_mcp_config prefers explicit path over MCP_CONFIG_PATH."""
        env_config = tmp_path / "env-config.yaml"
        env_config.write_text(_make_yaml_content(
            name="env", url="http://env/mcp"))
        explicit_config = tmp_path / "explicit-config.yaml"
        explicit_config.write_text(_make_yaml_content(
            name="explicit", url="http://explicit/mcp"))
        with patch.dict(os.environ, {"MCP_CONFIG_PATH": str(env_config)}):
            from agent_sandbox.config.loader import load_mcp_config

            config = load_mcp_config(explicit_config)

        assert config.servers[0].name == "explicit"

    def test_handles_multiple_interpolations(self, tmp_path: Path) -> None:
        """load_mcp_config handles multiple ${VAR} in same file."""
        config_file = tmp_path / "mcp-servers.yaml"
        config_file.write_text(f"""
servers:
  - name: {TEST_MCP_SERVER_NAME_TEXT}
    url: ${{TEXT_URL:-{TEST_MCP_SERVER_URL_TEXT}}}
  - name: {TEST_MCP_SERVER_NAME_NUMBERS}
    url: ${{NUMBERS_URL:-{TEST_MCP_SERVER_URL_NUMBERS}}}
""")
        text_override_url = "http://text:9001/mcp"
        with patch.dict(os.environ, {"TEXT_URL": text_override_url}):
            from agent_sandbox.config.loader import load_mcp_config

            config = load_mcp_config(config_file)

        assert config.servers[0].url == text_override_url
        assert config.servers[1].url == TEST_MCP_SERVER_URL_NUMBERS

    def test_handles_invalid_yaml(self, tmp_path: Path) -> None:
        """load_mcp_config returns empty config on invalid YAML."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("not: valid: yaml: here")

        from agent_sandbox.config.loader import load_mcp_config

        config = load_mcp_config(config_file)
        assert config.servers == []


class TestInterpolateEnvVars:
    """Tests for interpolate_env_vars helper function."""

    def test_replaces_simple_var(self) -> None:
        """interpolate_env_vars replaces ${VAR} with value."""
        from agent_sandbox.config.loader import interpolate_env_vars

        test_value = "my_value"
        with patch.dict(os.environ, {"MY_VAR": test_value}):
            result = interpolate_env_vars("prefix-${MY_VAR}-suffix")

        assert result == f"prefix-{test_value}-suffix"

    def test_uses_default_when_unset(self) -> None:
        """interpolate_env_vars uses default for ${VAR:-default}."""
        from agent_sandbox.config.loader import interpolate_env_vars

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("UNDEFINED_VAR", None)
            result = interpolate_env_vars("${UNDEFINED_VAR:-fallback}")

        assert result == "fallback"

    def test_empty_string_is_valid_value(self) -> None:
        """interpolate_env_vars treats empty string as set (not using default)."""
        from agent_sandbox.config.loader import interpolate_env_vars

        with patch.dict(os.environ, {"EMPTY_VAR": ""}):
            result = interpolate_env_vars("${EMPTY_VAR:-default}")

        # Empty string IS a value, so default should NOT be used
        assert result == ""

    def test_returns_empty_for_unset_without_default(self) -> None:
        """interpolate_env_vars returns empty string for unset var without default."""
        from agent_sandbox.config.loader import interpolate_env_vars

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TOTALLY_MISSING", None)
            result = interpolate_env_vars("${TOTALLY_MISSING}")

        assert result == ""

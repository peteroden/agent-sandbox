"""YAML configuration loader with environment variable interpolation.

This module provides utilities for loading MCP server configuration
from YAML files with support for ${VAR} and ${VAR:-default} patterns.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml

from agent_sandbox.config.mcp_config import MCPRegistryConfig

logger = logging.getLogger(__name__)

# Regex patterns for env var interpolation
# Matches ${VAR} or ${VAR:-default}
ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def interpolate_env_vars(value: str) -> str:
    """Replace ${VAR} and ${VAR:-default} patterns with environment values.

    Supports two patterns:
    - ${VAR}: Replace with env value, empty string if unset
    - ${VAR:-default}: Replace with env value, or default if unset

    Note: An empty string is considered a valid value (default not used).

    Args:
        value: String potentially containing ${VAR} patterns

    Returns:
        String with all ${VAR} patterns replaced
    """

    def replace_match(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default = match.group(2)  # None if no default specified

        # Check if variable is set (even to empty string)
        if var_name in os.environ:
            return os.environ[var_name]
        # Use default if provided, otherwise empty string
        return default if default is not None else ""

    return ENV_VAR_PATTERN.sub(replace_match, value)


def _interpolate_dict(data: Any) -> Any:
    """Recursively interpolate env vars in a dictionary structure.

    Args:
        data: Dictionary, list, or scalar value

    Returns:
        Same structure with string values interpolated
    """
    if isinstance(data, dict):
        return {k: _interpolate_dict(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_interpolate_dict(item) for item in data]
    if isinstance(data, str):
        return interpolate_env_vars(data)
    return data


def load_mcp_config(path: Path | None = None) -> MCPRegistryConfig:
    """Load MCP server configuration from YAML file.

    Loads configuration in the following order:
    1. Use explicit path if provided
    2. Use MCP_CONFIG_PATH environment variable
    3. Return empty config if no path available or file missing

    Supports ${VAR} and ${VAR:-default} interpolation in all string values.

    Args:
        path: Optional explicit path to config file

    Returns:
        MCPRegistryConfig with loaded servers (empty if file missing/invalid)
    """
    # Resolve config path
    config_path = path
    if config_path is None:
        env_path = os.environ.get("MCP_CONFIG_PATH")
        if env_path:
            config_path = Path(env_path)

    # Return empty config if no path
    if config_path is None:
        logger.debug("No config path specified, returning empty config")
        return MCPRegistryConfig(servers=[])

    # Return empty config if file doesn't exist
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}")
        return MCPRegistryConfig(servers=[])

    try:
        # Load YAML
        content = config_path.read_text()
        data = yaml.safe_load(content)

        if data is None:
            return MCPRegistryConfig(servers=[])

        # Interpolate environment variables
        data = _interpolate_dict(data)

        # Validate with Pydantic
        return MCPRegistryConfig.model_validate(data)

    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in {config_path}: {e}")
        return MCPRegistryConfig(servers=[])
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return MCPRegistryConfig(servers=[])

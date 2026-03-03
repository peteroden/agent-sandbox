"""Shared utility functions for mock clients.

Pure functions for tool detection, argument parsing, and result
extraction used by MockChatClient.
"""

from __future__ import annotations

import re
from typing import Any


def parse_integers(text: str) -> list[int]:
    """Extract all integers from a string."""
    return [int(n) for n in re.findall(r"-?\d+", text)]


TOOL_ALIASES: dict[str, str] = {
    "echo": "echo_text",
    "add": "add_numbers",
}


def detect_tool_request(
    message: str, tool_names: list[str]
) -> tuple[str | None, str]:
    """Detect ``use <tool_name> ...`` pattern in *message*.

    Supports short aliases (e.g. ``use echo`` for ``echo_text``).
    Returns ``(tool_name, remaining)`` or ``(None, message)``.
    """
    # Build lookup: alias → canonical name, plus each full name
    lookup: dict[str, str] = {}
    for name in tool_names:
        lookup[name] = name
    for alias, canonical in TOOL_ALIASES.items():
        if canonical in lookup:
            lookup[alias] = canonical

    # Match longest names first to avoid partial matches
    for name in sorted(lookup, key=len, reverse=True):
        match = re.search(
            rf"\buse\s+{re.escape(name)}\s*(.*)", message, re.IGNORECASE)
        if match:
            return lookup[name], match.group(1).strip()
    return None, message


# ---------------------------------------------------------------------------
# Tool introspection helpers (moved from MockChatClient class methods)
# ---------------------------------------------------------------------------

def get_available_tools(tools: list[Any]) -> list[tuple[str, Any]]:
    """Return ``[(tool_name, provider), ...]`` from a tools list."""
    result: list[tuple[str, Any]] = []
    for tool in tools:
        if hasattr(tool, "functions"):
            result.extend((f.name, tool) for f in tool.functions)
        elif isinstance(tool, dict) and tool.get("name") is not None:
            result.append((str(tool["name"]), tool))
        elif hasattr(tool, "name"):
            result.append((tool.name, tool))
    return result


def _get_tool_function(tool_name: str, provider: Any) -> Any | None:
    """Find the function object named *tool_name* on *provider*."""
    if hasattr(provider, "functions"):
        for func in provider.functions:
            if func.name == tool_name:
                return func
    return None


def _get_tool_parameters(func: Any) -> dict[str, Any]:
    """Extract the JSON-Schema parameters dict from *func*."""
    if func is None:
        return {}
    if hasattr(func, "parameters") and callable(func.parameters):
        params = func.parameters()
        return params if isinstance(params, dict) else {}
    if hasattr(func, "parameters") and isinstance(func.parameters, dict):
        return func.parameters
    return {}


def build_tool_args(
    tool_name: str, provider: Any, raw_args: str
) -> dict[str, Any] | None:
    """Build a kwargs dict for *tool_name* by parsing *raw_args*.

    Returns ``None`` when required parameters cannot be satisfied.
    """
    schema = _get_tool_parameters(_get_tool_function(tool_name, provider))
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    if not properties:
        return {"message": raw_args} if raw_args else {}

    result: dict[str, Any] = {}
    numbers = parse_integers(raw_args)
    num_idx = 0

    for param, meta in properties.items():
        ptype = meta.get("type", "string")
        if ptype == "integer":
            if num_idx < len(numbers):
                result[param] = numbers[num_idx]
                num_idx += 1
            elif param in required:
                return None
        else:
            result[param] = raw_args

    if any(r not in result for r in required):
        return None
    return result


# ---------------------------------------------------------------------------
# Tool-result extraction (MCP returns lists, framework returns strings)
# ---------------------------------------------------------------------------

def extract_tool_text(tool_message: Any) -> str:
    """Extract plain text from a tool-result ``Message``.

    Handles both string results and MCP-style list results like
    ``[{"type": "text", "text": "8"}]``.
    """
    for content in getattr(tool_message, "contents", None) or []:
        if getattr(content, "type", None) != "function_result":
            continue
        return _normalize_result(content.result)
    # Fall back to message text when no function_result content
    text = getattr(tool_message, "text", None)
    return text if text else ""


def _normalize_result(result: Any) -> str:
    """Convert a tool result to a plain string.

    Handles three formats:
    - Plain string: returned as-is
    - ``list[dict]``: MCP-style ``[{"type": "text", "text": "..."}]``
    - ``list[Content]``: framework Content objects with ``.text`` attribute
    """
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        parts: list[str] = []
        for item in result:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            elif isinstance(item, str):
                parts.append(item)
            elif hasattr(item, "text") and item.text is not None:
                parts.append(str(item.text))
        return " ".join(parts) if parts else str(result)
    # Single Content object with .text
    if hasattr(result, "text") and result.text is not None:
        return str(result.text)
    return str(result)

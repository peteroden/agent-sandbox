"""Shared utility functions for mock clients.

Pure functions for tool detection and argument parsing used by
MockChatClient.
"""

import re


def parse_integers(text: str) -> list[int]:
    """Extract all integers from a string.

    Args:
        text: String potentially containing numbers like "5 3" or "5, 3"

    Returns:
        List of parsed integers.

    Examples:
        >>> parse_integers("5 3")
        [5, 3]
        >>> parse_integers("add 10 and 20")
        [10, 20]
        >>> parse_integers("hello")
        []
    """
    return [int(n) for n in re.findall(r"-?\d+", text)]


def detect_tool_request(
    message: str, tool_names: list[str]
) -> tuple[str | None, str]:
    """Detect if message requests a tool execution.

    Looks for pattern "use <tool_name> ..." in the message.

    Args:
        message: The user's message to scan.
        tool_names: List of available tool names to match against.

    Returns:
        Tuple of (tool_name, remaining_message) where tool_name is None
        if no tool was requested. remaining_message is the text after
        "use <tool_name>".

    Examples:
        >>> detect_tool_request("use add_numbers 5 3", ["add_numbers"])
        ('add_numbers', '5 3')
        >>> detect_tool_request("hello world", ["add_numbers"])
        (None, 'hello world')
    """
    if not tool_names:
        return None, message

    for tool_name in tool_names:
        # Pattern: "use <tool_name>" followed by content
        pattern = rf"\buse\s+{re.escape(tool_name)}\s*(.*)"
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return tool_name, match.group(1).strip()

    return None, message

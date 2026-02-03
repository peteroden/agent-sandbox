"""Mock agent for development without Azure OpenAI."""

import logging
import re
import uuid
from collections.abc import AsyncIterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from agent_framework import (
    AgentResponse,
    AgentResponseUpdate,
    AgentThread,
    BaseAgent,
    ChatMessage,
    Content,
    Role,
)

logger = logging.getLogger(__name__)


@dataclass
class MockAgent(BaseAgent):
    """Mock agent for development without Azure OpenAI.

    Echoes back user messages with a prefix. Useful for testing
    the AG-UI integration without LLM API calls.

    Accepts tools in the same format as ChatAgent (list of MCPStreamableHTTPTool
    or other tool providers). Uses pattern matching ("use <tool_name> ...") to
    detect tool requests since there's no LLM to decide.
    """

    id: str = field(
        default_factory=lambda: f"mock-agent-{uuid.uuid4().hex[:8]}")
    name: str | None = "MockAgent"
    description: str | None = "A mock agent for development"
    response_prefix: str = field(default="[Mock] ")
    tools: list[Any] = field(default_factory=list)

    def get_new_thread(self, **kwargs: Any) -> AgentThread:
        """Create a new conversation thread."""
        return AgentThread()

    def _get_available_tools(self) -> list[tuple[str, Any]]:
        """Get list of (tool_name, tool_provider) from tools.

        Handles both MCPStreamableHTTPTool (which has .functions) and
        simple tool objects with a .name attribute.
        """
        result = []
        for tool in self.tools:
            # MCPStreamableHTTPTool has .functions property
            if hasattr(tool, "functions"):
                for func in tool.functions:
                    result.append((func.name, tool))
            # Dict-based tool info (for testing)
            elif isinstance(tool, dict):
                tool_name = tool.get("name")
                if tool_name is not None:
                    result.append((str(tool_name), tool))
            # Simple tool with name attribute
            elif hasattr(tool, "name"):
                result.append((tool.name, tool))
        return result

    def _get_tool_function(self, tool_name: str, tool_provider: Any) -> Any | None:
        """Get the function object for a tool from its provider.

        Returns:
            The function object with schema, or None if not found.
        """
        if hasattr(tool_provider, "functions"):
            for func in tool_provider.functions:
                if func.name == tool_name:
                    return func
        return None

    def _get_tool_parameters(self, func: Any) -> dict[str, Any]:
        """Extract parameter schema from a function object.

        Returns:
            Dict with 'properties' and 'required' keys from the schema.
        """
        if func is None:
            return {}
        # FunctionTool has parameters() method
        if hasattr(func, "parameters") and callable(func.parameters):
            params = func.parameters()
            return params if isinstance(params, dict) else {}
        # Mock objects may have parameters as a property
        if hasattr(func, "parameters") and isinstance(func.parameters, dict):
            return func.parameters
        return {}

    def _extract_last_user_message(
        self, messages: str | ChatMessage | Sequence[str | ChatMessage] | None
    ) -> str:
        """Extract the last user message from input."""
        if messages is None:
            return ""
        if isinstance(messages, str):
            return messages
        if isinstance(messages, ChatMessage):
            return (messages.text or "") if messages.role == Role.USER else ""

        # Sequence of messages - find the last user message
        for msg in reversed(list(messages)):
            if isinstance(msg, str):
                return msg
            if isinstance(msg, ChatMessage) and msg.role == Role.USER:
                return msg.text or ""
        return ""

    def _detect_tool_request(self, message: str) -> tuple[str | None, Any | None, str]:
        """Detect if message requests a tool execution.

        Args:
            message: The user's message

        Returns:
            Tuple of (tool_name, tool_provider, remaining_message) where
            tool_name is None if no tool was requested
        """
        available_tools = self._get_available_tools()
        if not available_tools:
            return None, None, message

        for tool_name, tool_provider in available_tools:
            # Pattern: "use <tool_name>" followed by content
            pattern = rf"\buse\s+{re.escape(tool_name)}\s*(.*)"
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return tool_name, tool_provider, match.group(1).strip()

        return None, None, message

    def _parse_numbers(self, args: str) -> list[int]:
        """Extract all integers from a string.

        Args:
            args: String potentially containing numbers like "5 3" or "5, 3"

        Returns:
            List of parsed integers.
        """
        return [int(n) for n in re.findall(r"-?\d+", args)]

    def _build_tool_args(
        self, tool_name: str, tool_provider: Any, args: str
    ) -> dict[str, Any] | None:
        """Build arguments dict for a tool call based on function schema.

        Uses the tool's parameter schema to determine expected argument types
        and parses the input string accordingly.

        Returns:
            Dict of arguments, or None if required args cannot be parsed.
        """
        func = self._get_tool_function(tool_name, tool_provider)
        schema = self._get_tool_parameters(func)
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # If no schema available, fall back to single string argument
        if not properties:
            return {"message": args}

        result: dict[str, Any] = {}
        numbers = self._parse_numbers(args)
        number_index = 0

        for param_name, param_schema in properties.items():
            param_type = param_schema.get("type", "string")

            if param_type == "integer":
                # Use next available number from parsed numbers
                if number_index < len(numbers):
                    result[param_name] = numbers[number_index]
                    number_index += 1
                elif param_name in required:
                    # Required integer but not enough numbers provided
                    return None
            elif param_type == "string":
                # Use the full input string for string parameters
                result[param_name] = args
            else:
                # For other types, try string representation
                result[param_name] = args

        # Verify all required parameters are present
        for req in required:
            if req not in result:
                return None

        return result

    async def _execute_tool_with_args(
        self, tool_name: str, tool_provider: Any, args_dict: dict[str, Any]
    ) -> str:
        """Execute a tool with pre-built arguments."""
        try:
            if hasattr(tool_provider, "call_tool"):
                result = await tool_provider.call_tool(tool_name, **args_dict)
                # Handle Content objects
                if isinstance(result, list):
                    texts = []
                    for c in result:
                        if hasattr(c, "text") and c.text:
                            texts.append(c.text)
                        else:
                            texts.append(str(c))
                    return " ".join(texts)
                return str(result)
            return f"Mock tool {tool_name} called with: {args_dict}"
        except Exception as e:
            logger.exception("Tool execution failed: %s", tool_name)
            return f"Tool error: {e}"

    async def run_stream(
        self,
        messages: str | ChatMessage | Sequence[str |
                                               ChatMessage] | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[AgentResponseUpdate]:
        """Yield streaming response updates with proper tool call events."""
        last_message = self._extract_last_user_message(messages)

        tool_name, tool_provider, remaining = self._detect_tool_request(
            last_message)

        if tool_name and tool_provider:
            # Build tool arguments from schema
            args_dict = self._build_tool_args(
                tool_name, tool_provider, remaining)

            if args_dict is None:
                # Invalid args - yield error message
                yield AgentResponseUpdate(
                    text=f"{self.response_prefix}Error: {tool_name} requires valid arguments",
                    role=Role.ASSISTANT,
                )
                return

            # Generate unique call ID
            call_id = f"call_{uuid.uuid4().hex[:12]}"

            # 1. Emit tool call - NO text in this update to avoid orphaned messages
            # The framework creates a "tool-only" message that never gets closed,
            # causing AG-UI client validation errors. This is a framework bug.
            yield AgentResponseUpdate(
                role=Role.ASSISTANT,
                contents=[
                    Content.from_function_call(
                        call_id=call_id,
                        name=tool_name,
                        arguments=args_dict,
                    )
                ],
            )

            # 2. Execute tool
            result = await self._execute_tool_with_args(
                tool_name, tool_provider, args_dict
            )

            # 3. Emit tool result
            yield AgentResponseUpdate(
                role=Role.TOOL,
                contents=[
                    Content.from_function_result(
                        call_id=call_id,
                        result=result,
                    )
                ],
            )
            # Note: We skip the final text response due to a framework bug.
            # The tool-only message created by the framework never gets
            # TEXT_MESSAGE_END, causing "@ag-ui/client" validation to fail
            # with "text messages are still active" error.
        else:
            # No tool - echo message
            content = f"{self.response_prefix}Echo: {last_message or 'No message'}"
            yield AgentResponseUpdate(text=content, role=Role.ASSISTANT)

    async def run(
        self,
        messages: str | ChatMessage | Sequence[str |
                                               ChatMessage] | None = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """Return a mock response by aggregating run_stream() output."""
        all_text = []
        async for update in self.run_stream(messages, **kwargs):
            if update.text:
                all_text.append(update.text)

        content = "".join(all_text) or "[Mock] No response"
        return AgentResponse(
            messages=ChatMessage(role=Role.ASSISTANT, text=content),
        )

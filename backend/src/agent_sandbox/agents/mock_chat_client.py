"""Mock chat client for development without Azure OpenAI.

Implements BaseChatClient to provide mock LLM responses for testing
the AG-UI integration without LLM API calls.
"""

import logging
import uuid
from collections.abc import AsyncIterable, MutableSequence
from typing import Any, ClassVar

from agent_framework import (
    BaseChatClient,
    ChatMessage,
    ChatResponse,
    ChatResponseUpdate,
    Content,
    Role,
)
from opentelemetry import trace

from agent_sandbox.agents.mock_utils import detect_tool_request, parse_integers

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("agent_sandbox.agents")


class MockChatClient(BaseChatClient):
    """Mock chat client for development without Azure OpenAI.

    Echoes back user messages with a prefix. Useful for testing
    the AG-UI integration without LLM API calls.

    Accepts tools in the same format as AzureOpenAIResponsesClient
    (list of MCPStreamableHTTPTool or other tool providers). Uses
    pattern matching ("use <tool_name> ...") to detect tool requests
    since there's no LLM to decide.
    """

    OTEL_PROVIDER_NAME: ClassVar[str] = "mock"
    MOCK_PREFIX: ClassVar[str] = "[Mock] "

    def __init__(self, *, tools: list[Any] | None = None, **kwargs: Any) -> None:
        """Initialize the mock chat client.

        Args:
            tools: Optional list of tool providers (MCPStreamableHTTPTool etc.)
            **kwargs: Additional arguments passed to BaseChatClient.
        """
        super().__init__(**kwargs)
        self.tools: list[Any] = tools or []

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
        self, messages: MutableSequence[ChatMessage]
    ) -> str:
        """Extract the last user message from input."""
        if not messages:
            return ""

        # Sequence of messages - find the last user message
        for msg in reversed(list(messages)):
            if isinstance(msg, ChatMessage) and msg.role == Role.USER:
                return msg.text or ""
        return ""

    def _detect_tool_request(self, message: str) -> tuple[str | None, Any | None, str]:
        """Detect if message requests a tool execution.

        Args:
            message: The user's message

        Returns:
            Tuple of (tool_name, tool_provider, remaining_message) where
            tool_name is None if no tool was requested.
        """
        available_tools = self._get_available_tools()
        if not available_tools:
            return None, None, message

        tool_names = [name for name, _ in available_tools]
        tool_map = {name: provider for name, provider in available_tools}

        matched_tool, remaining = detect_tool_request(message, tool_names)
        if matched_tool:
            return matched_tool, tool_map[matched_tool], remaining

        return None, None, message

    def _parse_numbers(self, args: str) -> list[int]:
        """Extract all integers from a string.

        Args:
            args: String potentially containing numbers like "5 3" or "5, 3"

        Returns:
            List of parsed integers.
        """
        return parse_integers(args)

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
        with tracer.start_as_current_span(
            "mock_chat.execute_tool",
            attributes={
                "tool.name": tool_name,
                "tool.args_count": len(args_dict),
            },
        ) as span:
            try:
                if hasattr(tool_provider, "call_tool"):
                    logger.info("Executing tool '%s' with args: %s",
                                tool_name, args_dict)
                    result = await tool_provider.call_tool(tool_name, **args_dict)
                    # Handle Content objects
                    if isinstance(result, list):
                        texts = []
                        for c in result:
                            if hasattr(c, "text") and c.text:
                                texts.append(c.text)
                            else:
                                texts.append(str(c))
                        result_str = " ".join(texts)
                    else:
                        result_str = str(result)
                    span.set_attribute("tool.success", True)
                    logger.info("Tool '%s' returned: %s",
                                tool_name, result_str)
                    return result_str
                result_str = f"Mock tool {tool_name} called with: {args_dict}"
                span.set_attribute("tool.success", True)
                span.set_attribute("tool.mock", True)
                return result_str
            except Exception as e:
                span.set_attribute("tool.success", False)
                span.set_attribute("error", str(e))
                span.record_exception(e)
                logger.exception("Tool execution failed: %s", tool_name)
                return f"Tool error: {e}"

    async def _inner_get_streaming_response(
        self,
        *,
        messages: MutableSequence[ChatMessage],
        options: dict[str, Any],
        **kwargs: Any,
    ) -> AsyncIterable[ChatResponseUpdate]:
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
                yield ChatResponseUpdate(
                    text=f"{self.MOCK_PREFIX}Error: {tool_name} requires valid arguments",
                    role=Role.ASSISTANT,
                )
                return

            # Generate unique call ID
            call_id = f"call_{uuid.uuid4().hex[:12]}"

            # 1. Emit tool call
            yield ChatResponseUpdate(
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
            yield ChatResponseUpdate(
                role=Role.TOOL,
                contents=[
                    Content.from_function_result(
                        call_id=call_id,
                        result=result,
                    )
                ],
            )
        else:
            # No tool - echo message with prefix
            content = f"{self.MOCK_PREFIX}Echo: {last_message or 'No message'}"
            yield ChatResponseUpdate(text=content, role=Role.ASSISTANT)

    async def _inner_get_response(
        self,
        *,
        messages: MutableSequence[ChatMessage],
        options: dict[str, Any],
        **kwargs: Any,
    ) -> ChatResponse:
        """Return a mock response by aggregating streaming output."""
        all_text: list[str] = []
        all_contents: list[Content] = []

        async for update in self._inner_get_streaming_response(
            messages=messages, options=options, **kwargs
        ):
            if update.text:
                all_text.append(update.text)
            if update.contents:
                all_contents.extend(update.contents)

        response_text = "".join(all_text) or f"{self.MOCK_PREFIX}No response"

        return ChatResponse(
            messages=[
                ChatMessage(
                    role=Role.ASSISTANT,
                    text=response_text,
                    contents=all_contents if all_contents else None,
                )
            ],
        )

"""Mock chat client using @use_function_invocation for tool execution.

The decorator wraps get_streaming_response to intercept FunctionCallContent,
execute tools automatically, and call us again with results in messages.
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
    use_function_invocation,
)

from agent_sandbox.agents.mock_utils import (
    build_tool_args,
    detect_tool_request,
    extract_tool_text,
    get_available_tools,
)

logger = logging.getLogger(__name__)


@use_function_invocation
class MockChatClient(BaseChatClient):
    """Mock LLM client that echoes messages and pattern-matches tool requests.

    Uses ``use <tool_name> <args>`` syntax to detect tool calls since
    there is no real LLM to decide.
    """

    OTEL_PROVIDER_NAME: ClassVar[str] = "mock"
    MOCK_PREFIX: ClassVar[str] = "[Mock] "

    def __init__(self, *, tools: list[Any] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tools: list[Any] = tools or []

    async def _inner_get_streaming_response(
        self,
        *,
        messages: MutableSequence[ChatMessage],
        options: dict[str, Any],
        **kwargs: Any,
    ) -> AsyncIterable[ChatResponseUpdate]:
        """Yield streaming updates -- function-call or plain echo.

        The decorator calls us twice for tool requests:
        1. We emit FunctionCallContent -> decorator executes the tool.
        2. Decorator calls us again with tool-result messages -> we
           extract and return the result text.
        """
        # Callback with tool results -- extract text and return
        if messages and messages[-1].role == Role.TOOL:
            yield ChatResponseUpdate(
                text=extract_tool_text(messages[-1]),
                role=Role.ASSISTANT,
            )
            return

        # Find last user message
        user_text = ""
        for msg in reversed(list(messages)):
            if isinstance(msg, ChatMessage) and msg.role == Role.USER:
                user_text = msg.text or ""
                break

        # Detect tool pattern
        available = get_available_tools(self.tools)
        tool_names = [name for name, _ in available]
        tool_map = dict(available)
        matched, remaining = detect_tool_request(user_text, tool_names)

        if matched:
            args = build_tool_args(matched, tool_map[matched], remaining)
            if args is None:
                yield ChatResponseUpdate(
                    text=f"{self.MOCK_PREFIX}Error: {matched} requires valid arguments",
                    role=Role.ASSISTANT,
                )
                return
            yield ChatResponseUpdate(
                role=Role.ASSISTANT,
                contents=[
                    Content.from_function_call(
                        call_id=f"call_{uuid.uuid4().hex[:12]}",
                        name=matched,
                        arguments=args,
                    )
                ],
            )
        else:
            yield ChatResponseUpdate(
                text=f"{self.MOCK_PREFIX}Echo: {user_text or 'No message'}",
                role=Role.ASSISTANT,
            )

    async def _inner_get_response(
        self,
        *,
        messages: MutableSequence[ChatMessage],
        options: dict[str, Any],
        **kwargs: Any,
    ) -> ChatResponse:
        """Aggregate streaming output into a single response."""
        texts: list[str] = []
        contents: list[Content] = []

        async for update in self._inner_get_streaming_response(
            messages=messages, options=options, **kwargs
        ):
            if update.text:
                texts.append(update.text)
            if update.contents:
                contents.extend(update.contents)

        return ChatResponse(
            messages=[
                ChatMessage(
                    role=Role.ASSISTANT,
                    text="".join(texts) or f"{self.MOCK_PREFIX}No response",
                    contents=contents or None,
                )
            ],
        )

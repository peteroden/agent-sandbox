"""Mock chat client for tool execution.

Agent framework rc1 handles function invocation automatically via
the Agent class. This client provides the streaming response logic.
"""

import logging
import uuid
from collections.abc import AsyncIterable, Mapping, Sequence
from typing import Any, Awaitable, ClassVar

from agent_framework import (
    BaseChatClient,
    ChatResponse,
    ChatResponseUpdate,
    Content,
    FunctionInvocationLayer,
    Message,
    ResponseStream,
)

from agent_sandbox.agents.mock_utils import (
    build_tool_args,
    detect_tool_request,
    extract_tool_text,
    get_available_tools,
)

logger = logging.getLogger(__name__)


class MockChatClient(FunctionInvocationLayer, BaseChatClient):
    """Mock LLM client that echoes messages and pattern-matches tool requests.

    Uses ``use <tool_name> <args>`` syntax to detect tool calls since
    there is no real LLM to decide.
    """

    OTEL_PROVIDER_NAME: ClassVar[str] = "mock"
    MOCK_PREFIX: ClassVar[str] = "[Mock] "

    def __init__(self, *, tools: list[Any] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tools: list[Any] = tools or []

    async def _generate_updates(
        self,
        *,
        messages: Sequence[Message],
        options: Mapping[str, Any],
        **kwargs: Any,
    ) -> AsyncIterable[ChatResponseUpdate]:
        """Yield streaming updates -- function-call or plain echo."""
        # Callback with tool results -- extract text and return
        if messages and messages[-1].role == "tool":
            yield ChatResponseUpdate(
                contents=[Content.from_text(text=extract_tool_text(messages[-1]))],
                role="assistant",
            )
            return

        # Find last user message
        user_text = ""
        for msg in reversed(list(messages)):
            if isinstance(msg, Message) and msg.role == "user":
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
                    contents=[Content.from_text(
                        text=f"{self.MOCK_PREFIX}Error: {matched} requires valid arguments",
                    )],
                    role="assistant",
                )
                return
            yield ChatResponseUpdate(
                role="assistant",
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
                contents=[Content.from_text(
                    text=f"{self.MOCK_PREFIX}Echo: {user_text or 'No message'}",
                )],
                role="assistant",
            )

    def _inner_get_response(
        self,
        *,
        messages: Sequence[Message],
        stream: bool,
        options: Mapping[str, Any],
        **kwargs: Any,
    ) -> Awaitable[ChatResponse] | ResponseStream[ChatResponseUpdate, ChatResponse]:
        """Return response or stream based on the stream flag."""
        if stream:
            return self._build_response_stream(
                self._generate_updates(messages=messages, options=options, **kwargs)
            )
        return self._build_non_streaming_response(
            messages=messages, options=options, **kwargs
        )

    async def _build_non_streaming_response(
        self,
        *,
        messages: Sequence[Message],
        options: Mapping[str, Any],
        **kwargs: Any,
    ) -> ChatResponse:
        """Aggregate streaming output into a single response."""
        texts: list[str] = []
        contents: list[Content] = []

        async for update in self._generate_updates(
            messages=messages, options=options, **kwargs
        ):
            if update.text:
                texts.append(update.text)
            if update.contents:
                contents.extend(update.contents)

        return ChatResponse(
            messages=[
                Message(
                    role="assistant",
                    text="".join(texts) or f"{self.MOCK_PREFIX}No response",
                    contents=contents or None,
                )
            ],
        )

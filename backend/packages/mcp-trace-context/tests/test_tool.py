"""Tests for TracingTool wrapper."""

from mcp_trace_context import TracingTool
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# TracingTool requires agent-framework, so we skip if not available
pytest.importorskip("agent_framework")


class TestTracingTool:
    """Tests for TracingTool wrapper."""

    @pytest.mark.asyncio
    async def test_injects_meta_on_call_tool(self):
        """TracingTool injects _meta with trace context on call_tool."""
        tool = TracingTool(url="http://localhost:8001/mcp")

        with patch.object(tool, "_call_mcp_tool", new_callable=AsyncMock) as mock:
            mock.return_value = []
            # Mock the parent class's call_tool
            with patch(
                "mcp_trace_context._tool.MCPStreamableHTTPTool.call_tool",
                new_callable=AsyncMock,
            ) as super_mock:
                super_mock.return_value = "result"

                await tool.call_tool("my_tool", arg="value")

                # Verify _meta was passed
                super_mock.assert_called_once()
                call_kwargs = super_mock.call_args.kwargs
                assert "_meta" in call_kwargs
                # _meta should be a dict (may be empty if no active span)
                assert isinstance(call_kwargs["_meta"], dict)

    @pytest.mark.asyncio
    async def test_preserves_original_arguments(self):
        """TracingTool preserves other arguments passed to call_tool."""
        tool = TracingTool(url="http://localhost:8001/mcp")

        with patch(
            "mcp_trace_context._tool.MCPStreamableHTTPTool.call_tool",
            new_callable=AsyncMock,
        ) as super_mock:
            super_mock.return_value = "result"

            await tool.call_tool("my_tool", arg1="value1", arg2=42)

            call_args, call_kwargs = super_mock.call_args
            assert call_args == ("my_tool",)
            assert call_kwargs["arg1"] == "value1"
            assert call_kwargs["arg2"] == 42

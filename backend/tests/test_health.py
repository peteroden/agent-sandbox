"""Tests for health check utility."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from agent_sandbox.health import (
    DEFAULT_SERVICES,
    ServiceStatus,
    check_all_services,
    check_service_health,
    format_status_table,
)
from tests.conftest import TEST_SERVICE_NAME, TEST_SERVICE_URL


class TestCheckServiceHealth:
    """Tests for check_service_health function."""

    def test_returns_healthy_for_200_response(self) -> None:
        """Returns healthy status when service responds with 200."""
        with patch("agent_sandbox.health.httpx.get", return_value=MagicMock(status_code=200)):
            status = check_service_health(TEST_SERVICE_NAME, TEST_SERVICE_URL)

        assert status == ServiceStatus(
            name=TEST_SERVICE_NAME, url=TEST_SERVICE_URL, healthy=True)

    @pytest.mark.parametrize(
        ("status_code", "exception", "expected_error"),
        [
            (500, None, "HTTP 500"),
            (None, httpx.ConnectError("refused"), "refused"),
            (None, httpx.TimeoutException("timeout"), "timeout"),
        ],
    )
    def test_returns_unhealthy_for_errors(
        self, status_code: int | None, exception: Exception | None, expected_error: str
    ) -> None:
        """Returns unhealthy status for non-200 or connection errors."""
        if exception:
            mock = patch("agent_sandbox.health.httpx.get",
                         side_effect=exception)
        else:
            mock = patch(
                "agent_sandbox.health.httpx.get", return_value=MagicMock(status_code=status_code)
            )

        with mock:
            status = check_service_health(TEST_SERVICE_NAME, TEST_SERVICE_URL)

        assert status.healthy is False
        assert expected_error in (status.error or "")


class TestCheckAllServices:
    """Tests for check_all_services function."""

    def test_uses_default_services_when_none_provided(self) -> None:
        """Uses DEFAULT_SERVICES when no custom list provided."""
        with patch("agent_sandbox.health.httpx.get", return_value=MagicMock(status_code=200)):
            results = check_all_services()

        assert len(results) == len(DEFAULT_SERVICES)

    def test_uses_custom_services_when_provided(self) -> None:
        """Uses custom services list when provided."""
        custom = [("svc1", "http://localhost:9001"),
                  ("svc2", "http://localhost:9002")]

        with patch("agent_sandbox.health.httpx.get", return_value=MagicMock(status_code=200)):
            results = check_all_services(services=custom)

        assert [r.name for r in results] == ["svc1", "svc2"]


class TestFormatStatusTable:
    """Tests for format_status_table function."""

    @pytest.mark.parametrize(
        ("healthy", "error", "expected_indicator"),
        [
            (True, None, "✓"),
            (False, "Connection refused", "✗"),
        ],
    )
    def test_formats_status_with_correct_indicator(
        self, healthy: bool, error: str | None, expected_indicator: str
    ) -> None:
        """Formats services with correct status indicator."""
        status = ServiceStatus(
            name=TEST_SERVICE_NAME, url=TEST_SERVICE_URL, healthy=healthy, error=error
        )
        output = format_status_table([status])

        assert TEST_SERVICE_NAME in output
        assert expected_indicator in output
        if error:
            assert error in output


class TestDefaultServices:
    """Tests for DEFAULT_SERVICES configuration."""

    @pytest.mark.parametrize(
        "expected_name",
        ["AG-UI Server", "Text MCP", "Number MCP", "Frontend"],
    )
    def test_contains_required_service(self, expected_name: str) -> None:
        """DEFAULT_SERVICES contains all required entries."""
        names = [name for name, _ in DEFAULT_SERVICES]
        assert expected_name in names

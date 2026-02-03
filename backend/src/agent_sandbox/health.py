"""Health check utility for local development services."""

from dataclasses import dataclass

import httpx

# Default services to check for local development
DEFAULT_SERVICES: list[tuple[str, str]] = [
    ("AG-UI Server", "http://localhost:8888/health"),
    ("Text MCP", "http://localhost:8001/health"),
    ("Number MCP", "http://localhost:8002/health"),
    ("Frontend", "http://localhost:5173"),
]


@dataclass
class ServiceStatus:
    """Status of a single service health check."""

    name: str
    url: str
    healthy: bool
    error: str | None = None


def check_service_health(name: str, url: str, timeout: float = 5.0) -> ServiceStatus:
    """Check the health of a single service.

    Args:
        name: Human-readable service name.
        url: URL to check (HTTP GET).
        timeout: Request timeout in seconds.

    Returns:
        ServiceStatus with health check result.
    """
    try:
        response = httpx.get(url, timeout=timeout)
        if response.status_code == 200:
            return ServiceStatus(name=name, url=url, healthy=True)
        return ServiceStatus(
            name=name,
            url=url,
            healthy=False,
            error=f"HTTP {response.status_code}",
        )
    except httpx.TimeoutException as e:
        return ServiceStatus(name=name, url=url, healthy=False, error=str(e))
    except httpx.ConnectError as e:
        return ServiceStatus(name=name, url=url, healthy=False, error=str(e))
    except httpx.HTTPError as e:
        return ServiceStatus(name=name, url=url, healthy=False, error=str(e))


def check_all_services(
    services: list[tuple[str, str]] | None = None,
) -> list[ServiceStatus]:
    """Check health of all configured services.

    Args:
        services: Optional list of (name, url) tuples. Defaults to DEFAULT_SERVICES.

    Returns:
        List of ServiceStatus for each service.
    """
    if services is None:
        services = DEFAULT_SERVICES

    return [check_service_health(name, url) for name, url in services]


def format_status_table(statuses: list[ServiceStatus]) -> str:
    """Format service statuses as a colored table for terminal output.

    Args:
        statuses: List of ServiceStatus to format.

    Returns:
        Formatted string with status table.
    """
    # ANSI color codes
    green = "\033[32m"
    red = "\033[31m"
    reset = "\033[0m"
    bold = "\033[1m"

    lines = [
        f"{bold}Service Health Check{reset}",
        "=" * 60,
    ]

    for status in statuses:
        if status.healthy:
            indicator = f"{green}✓ OK{reset}"
            error_msg = ""
        else:
            indicator = f"{red}✗ FAIL{reset}"
            error_msg = f" - {status.error}" if status.error else ""

        lines.append(f"{status.name:<20} {indicator}{error_msg}")
        lines.append(f"  {status.url}")

    lines.append("=" * 60)

    # Summary
    healthy_count = sum(1 for s in statuses if s.healthy)
    total_count = len(statuses)

    if healthy_count == total_count:
        summary = f"{green}All {total_count} services healthy{reset}"
    else:
        summary = f"{red}{total_count - healthy_count}/{total_count} services unhealthy{reset}"

    lines.append(summary)

    return "\n".join(lines)


if __name__ == "__main__":
    results = check_all_services()
    print(format_status_table(results))

    # Exit with non-zero if any service is unhealthy
    unhealthy_count = sum(1 for s in results if not s.healthy)
    exit(unhealthy_count)

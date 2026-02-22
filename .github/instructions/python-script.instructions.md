---
description: "Instructions for Python scripting implementation with TDD and SOLID principles"
applyTo: "**/*.py"
---

# Python Script Instructions

Conventions for Python 3.11+ scripts used in automation, tooling, and CLI applications. All code follows TDD (Test-Driven Development) and SOLID principles.

## TDD Workflow

All Python code follows a strict TDD approach:

1. **Red**: Write a failing test first that describes the expected behavior.
2. **Green**: Write the minimum code to make the test pass.
3. **Refactor**: Improve the code while keeping tests green.

Never write implementation code without a corresponding test. Tests live in a `tests/` directory mirroring the source structure.

## SOLID Principles

Apply SOLID principles throughout:

- **Single Responsibility**: Each class/function has one reason to change.
- **Open/Closed**: Open for extension, closed for modification.
- **Liskov Substitution**: Subtypes must be substitutable for their base types.
- **Interface Segregation**: Many specific interfaces over one general interface.
- **Dependency Inversion**: Depend on abstractions, not concretions. Use dependency injection.

## Entry Points and Exit Codes

```python
import sys

EXIT_SUCCESS = 0  # Successful execution
EXIT_FAILURE = 1  # General failure
EXIT_ERROR = 2    # Arguments or configuration error


def main() -> int:
    """Main entry point for the script."""
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
```

Standard exit codes: 0 success, 1 failure, 2 configuration error, 130 user interrupt (SIGINT).

## CLI Argument Parsing

### argparse

Extract parser creation into a separate function for testability.

```python
import argparse
from pathlib import Path


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(description="Process files")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-o", "--output", type=Path, default=Path("output.txt"))
    parser.add_argument("input_file", type=Path)
    return parser
```

Use `type=Path` for file arguments and `action="store_true"` for boolean flags.

### click

For complex CLIs with subcommands or interactive prompts, use the click framework.

```python
import click


@click.command()
@click.option("-v", "--verbose", is_flag=True)
@click.argument("input_file", type=click.Path(exists=True))
@click.pass_context
def main(ctx: click.Context, verbose: bool, input_file: str) -> None:
    """Process input files."""
    ctx.exit(0)  # Explicit exit code
```

## Logging Configuration

```python
import logging

logger = logging.getLogger(__name__)


def configure_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
```

Create module-level logger, configure early in main.

## Path Handling

Use pathlib.Path exclusively; avoid os.path.

```python
from pathlib import Path


def process_file(path: Path) -> None:
    """Read, process, and write file content."""
    content = path.read_text(encoding="utf-8")
    processed = transform_content(content)
    output_path = path.with_suffix(".out")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(processed, encoding="utf-8")
```

Common patterns: `cwd()`, `resolve()`, `exists()`, `is_dir()`, `is_file()`, `iterdir()`, `glob()`, `rglob()`, `read_text()`, `write_text()`, `mkdir(parents=True, exist_ok=True)`, `parent`, `name`, `stem`, `suffix`.

## Subprocess Execution

Use subprocess.run() with error handling.

```python
import subprocess
import os
from pathlib import Path


def run_command(cmd: list[str], cwd: Path | None = None, extra_env: dict[str, str] | None = None) -> str:
    """Run command and return stdout, raising on failure."""
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=cwd, env=env)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error("Command failed: %s\nstderr: %s", e.returncode, e.stderr)
        raise
    except FileNotFoundError:
        logger.error("Command not found: %s", cmd[0])
        raise
```

Use `capture_output=True` and `text=True` for string output. Use `check=True` to raise on non-zero exit.

## Type Hints

Use Python 3.11+ syntax with built-in generics.

```python
from pathlib import Path
from typing import Literal, Self


def process_items(items: list[str]) -> dict[str, int]:  # Built-in generics
    return {item: len(item) for item in items}


def read_file(path: str | Path) -> str:  # Union with pipe
    return Path(path).read_text(encoding="utf-8")


def find_config(name: str) -> Path | None:  # Optional with pipe
    config = Path(name)
    return config if config.exists() else None


def set_level(level: Literal["debug", "info", "warning"]) -> None:  # Constrained values
    pass


class Builder:
    def add(self, item: str) -> Self:  # Fluent interface
        self.items.append(item)
        return self
```

Use `list[str]` not `typing.List[str]`, `str | None` not `Optional[str]`, `Literal` for constrained values, `Self` for chained methods.

## Pydantic Models

Use Pydantic for all data models, configuration, and API request/response types.

```python
from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Request model for agent invocation."""

    message: str = Field(..., min_length=1, description="User message")
    context: list[str] = Field(default_factory=list, description="Previous context")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class AgentResponse(BaseModel):
    """Response model from agent."""

    content: str
    tokens_used: int
    model: str
```

Benefits:

- Automatic validation and serialization
- Clear schema documentation
- IDE autocompletion support
- Easy JSON serialization for APIs

## Error Handling

Handle interrupts and pipe errors at the top level.

```python
import sys


def main() -> int:
    """Main entry point with error handling."""
    try:
        return run()
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except BrokenPipeError:
        sys.stderr.close()
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
```

Custom exceptions can carry exit codes:

```python
class ScriptError(Exception):
    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code
```

## Documentation

Use Google-style docstrings with Args, Returns, Raises, and Example sections.

```python
def process_data(data: list[str], *, normalize: bool = False) -> dict[str, int]:
    """Process input data and return statistics.

    Args:
        data: List of strings to process.
        normalize: If True, normalize values before processing.

    Returns:
        Dictionary mapping processed items to their counts.

    Raises:
        ValueError: If data is empty.

    Example:
        >>> process_data(["a", "b", "a"])
        {'a': 2, 'b': 1}
    """
```

Include module docstrings with description, usage, and examples.

## Script Organization

Organize scripts in this order:

1. Shebang: `#!/usr/bin/env python3`
2. Future imports: `from __future__ import annotations`
3. Imports: standard library, third-party, local (separated by blank lines)
4. Constants and exit codes
5. Module-level logger
6. Helper functions
7. Parser creation function
8. Logging configuration function
9. Run logic function
10. Main entry point
11. Module guard: `if __name__ == "__main__": sys.exit(main())`

## Inline Script Metadata

PEP 723 inline metadata enables automatic dependency installation with uv.

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "click>=8.0",
#     "rich>=13.0",
# ]
# ///
```

Place after shebang, before module docstring. Run with `uv run script.py`.

## Azure OpenAI Integration

Use dependency injection for LLM clients to enable testing with mocks.

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def complete(self, prompt: str) -> str:
        """Generate completion for prompt."""
        pass


class AzureOpenAIClient(LLMClient):
    """Production Azure OpenAI client."""

    def __init__(self, endpoint: str, api_key: str, deployment: str) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment = deployment

    async def complete(self, prompt: str) -> str:
        # Implementation using Azure OpenAI SDK
        pass


class MockLLMClient(LLMClient):
    """Mock client for testing."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = responses or ["Mock response"]
        self._call_count = 0

    async def complete(self, prompt: str) -> str:
        response = self.responses[self._call_count % len(self.responses)]
        self._call_count += 1
        return response


def create_llm_client() -> LLMClient:
    """Factory function respecting USE_MOCK_LLM environment variable."""
    import os

    if os.getenv("USE_MOCK_LLM", "").lower() == "true":
        return MockLLMClient()

    return AzureOpenAIClient(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    )
```

Set `USE_MOCK_LLM=true` for development and testing without API calls.

## Testing with pytest

Structure tests to match source layout:

```
backend/
├── src/
│   └── agent/
│       └── client.py
└── tests/
    └── agent/
        └── test_client.py
```

### Testing Philosophy

**Test our code, not third-party packages.** Focus tests on the behavior of your own code. Mock external dependencies at the boundary. Do not test that libraries work correctly—trust their own test suites.

```python
# BAD: Testing that httpx works
async def test_httpx_makes_request():
    response = await httpx.get("https://api.example.com")
    assert response.status_code == 200  # Testing httpx, not our code

# GOOD: Testing our code's behavior with mocked dependency
async def test_client_returns_parsed_data(mock_http_client):
    mock_http_client.get.return_value = {"name": "test"}
    result = await our_client.fetch_user("123")
    assert result.name == "test"  # Testing our parsing logic
```

### Avoid Magic Strings

Define constants for test values to improve readability and maintainability.

```python
# BAD: Magic strings scattered throughout tests
def test_user_creation():
    user = User(name="John Doe", email="john@example.com")
    assert user.name == "John Doe"

# GOOD: Use constants
class TestUserDefaults:
    NAME = "Test User"
    EMAIL = "test@example.com"
    USER_ID = "user-123"

def test_user_creation():
    user = User(name=TestUserDefaults.NAME, email=TestUserDefaults.EMAIL)
    assert user.name == TestUserDefaults.NAME
```

### Parameterized Tests

Use `@pytest.mark.parametrize` for testing multiple scenarios with shared logic.

```python
import pytest

# BAD: Repetitive individual tests
def test_validate_empty_string():
    assert validate("") is False

def test_validate_whitespace():
    assert validate("   ") is False

def test_validate_valid_input():
    assert validate("hello") is True

# GOOD: Parameterized test
@pytest.mark.parametrize(
    "input_value,expected",
    [
        ("", False),
        ("   ", False),
        ("hello", True),
        ("hello world", True),
    ],
    ids=["empty", "whitespace", "single-word", "multi-word"],
)
def test_validate_input(input_value: str, expected: bool):
    assert validate(input_value) is expected
```

### Keep Tests Concise

Each test should verify one behavior. Use fixtures to reduce boilerplate.

```python
import pytest
from unittest.mock import AsyncMock


@pytest.fixture
def mock_llm():
    """Provide mock LLM client for testing."""
    return MockLLMClient(responses=["Test response"])


@pytest.fixture
def agent(mock_llm):
    """Provide agent with mock dependencies."""
    return Agent(llm_client=mock_llm)


async def test_agent_responds(agent):
    """Agent should return LLM response."""
    response = await agent.process("Hello")
    assert response == "Test response"
```

### Testing Boundaries

Mock at the integration boundary, not deep within your code:

```python
# BAD: Mocking internal implementation details
def test_service_with_deep_mocks(mocker):
    mocker.patch("package.internal.module._private_helper")
    # Brittle: breaks when internals change

# GOOD: Mock at the boundary (injected dependency)
def test_service_with_injected_mock(mock_http_client):
    service = UserService(http_client=mock_http_client)
    # Stable: only tests our service's interface
```

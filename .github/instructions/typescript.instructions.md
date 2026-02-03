---
description: "Instructions for TypeScript development with TDD and SOLID principles targeting TypeScript 5.x and ES2022"
applyTo: "**/*.ts, **/*.tsx"
---

# TypeScript Development Instructions

Guidelines for TypeScript development targeting TypeScript 5.x and ES2022 output. All code follows TDD (Test-Driven Development) and SOLID principles.

## TDD Workflow

All TypeScript code follows a strict TDD approach:

1. **Red**: Write a failing test first that describes the expected behavior
2. **Green**: Write the minimum code to make the test pass
3. **Refactor**: Improve the code while keeping tests green

Never write implementation code without a corresponding test. Tests live alongside source files or in a dedicated `test/` directory.

## SOLID Principles

Apply SOLID principles throughout:

- **Single Responsibility**: Each class/function has one reason to change
- **Open/Closed**: Open for extension, closed for modification
- **Liskov Substitution**: Subtypes must be substitutable for their base types
- **Interface Segregation**: Many specific interfaces over one general interface
- **Dependency Inversion**: Depend on abstractions, not concretions. Use dependency injection

## Core Intent

- Respect the existing architecture and coding standards
- Prefer readable, explicit solutions over clever shortcuts
- Extend current abstractions before inventing new ones
- Prioritize maintainability and clarity, short methods and classes, clean code

## General Guardrails

- Target TypeScript 5.x / ES2022 and prefer native features over polyfills
- Use pure ES modules; never emit `require`, `module.exports`, or CommonJS helpers
- Rely on the project's build, lint, and test scripts unless asked otherwise
- Note design trade-offs when intent is not obvious

## Project Organization

- Follow the repository's folder and responsibility layout for new code
- Use kebab-case filenames (e.g., `user-session.ts`, `data-service.ts`) unless told otherwise
- Keep tests, types, and helpers near their implementation when it aids discovery
- Reuse or extend shared utilities before adding new ones

## Naming & Style

- Use PascalCase for classes, interfaces, enums, and type aliases; camelCase for everything else
- Skip interface prefixes like `I`; rely on descriptive names
- Name things for their behavior or domain meaning, not implementation

## Formatting & Style

- Run the repository's lint/format scripts (e.g., `npm run lint`) before submitting
- Match the project's indentation, quote style, and trailing comma rules
- Keep functions focused; extract helpers when logic branches grow
- Favor immutable data and pure functions when practical

## Type System Expectations

- Avoid `any` (implicit or explicit); prefer `unknown` plus narrowing
- Use discriminated unions for realtime events and state machines
- Centralize shared contracts instead of duplicating shapes
- Express intent with TypeScript utility types (e.g., `Readonly`, `Partial`, `Record`)

```typescript
// Discriminated union for state machine
type ConnectionState =
  | { status: "disconnected" }
  | { status: "connecting"; attempt: number }
  | { status: "connected"; sessionId: string }
  | { status: "error"; error: Error };

// Type narrowing with unknown
function processResponse(data: unknown): string {
  if (typeof data === "object" && data !== null && "message" in data) {
    return (data as { message: string }).message;
  }
  throw new Error("Invalid response format");
}
```

## Async, Events & Error Handling

- Use `async/await`; wrap awaits in try/catch with structured errors
- Guard edge cases early to avoid deep nesting
- Send errors through the project's logging/telemetry utilities
- Surface user-facing errors via the repository's notification pattern
- Debounce configuration-driven updates and dispose resources deterministically

```typescript
async function fetchData(url: string): Promise<Result<Data, AppError>> {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      return { success: false, error: new HttpError(response.status) };
    }
    const data = await response.json();
    return { success: true, value: data };
  } catch (error) {
    return { success: false, error: new NetworkError(error) };
  }
}
```

## Architecture & Patterns

- Follow the repository's dependency injection or composition pattern; keep modules single-purpose
- Observe existing initialization and disposal sequences when wiring into lifecycles
- Keep transport, domain, and presentation layers decoupled with clear interfaces
- Supply lifecycle hooks (e.g., `initialize`, `dispose`) and targeted tests when adding services

```typescript
// Dependency injection pattern
interface Logger {
  info(message: string): void;
  error(message: string, error?: Error): void;
}

interface HttpClient {
  get<T>(url: string): Promise<T>;
  post<T>(url: string, body: unknown): Promise<T>;
}

class UserService {
  constructor(
    private readonly httpClient: HttpClient,
    private readonly logger: Logger,
  ) {}

  async getUser(id: string): Promise<User> {
    this.logger.info(`Fetching user ${id}`);
    return this.httpClient.get<User>(`/users/${id}`);
  }
}
```

## External Integrations

- Instantiate clients outside hot paths and inject them for testability
- Never hardcode secrets; load them from secure sources
- Apply retries, backoff, and cancellation to network or IO calls
- Normalize external responses and map errors to domain shapes

## Security Practices

- Validate and sanitize external input with schema validators or type guards
- Avoid dynamic code execution and untrusted template rendering
- Encode untrusted content before rendering HTML; use framework escaping or trusted types
- Use parameterized queries or prepared statements to block injection
- Keep secrets in secure storage, rotate them regularly, and request least-privilege scopes
- Favor immutable flows and defensive copies for sensitive data

## Configuration & Secrets

- Reach configuration through shared helpers and validate with schemas
- Handle secrets via the project's secure storage; guard `undefined` and error states
- Document new configuration keys and update related tests

## Testing Patterns

Write tests using the project's testing framework (Vitest for this project):

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";

describe("UserService", () => {
  let mockHttpClient: HttpClient;
  let mockLogger: Logger;
  let userService: UserService;

  beforeEach(() => {
    mockHttpClient = {
      get: vi.fn(),
      post: vi.fn(),
    };
    mockLogger = {
      info: vi.fn(),
      error: vi.fn(),
    };
    userService = new UserService(mockHttpClient, mockLogger);
  });

  it("fetches user by id", async () => {
    const expectedUser = { id: "123", name: "Test User" };
    vi.mocked(mockHttpClient.get).mockResolvedValue(expectedUser);

    const user = await userService.getUser("123");

    expect(user).toEqual(expectedUser);
    expect(mockHttpClient.get).toHaveBeenCalledWith("/users/123");
  });

  it("logs info when fetching user", async () => {
    vi.mocked(mockHttpClient.get).mockResolvedValue({ id: "123" });

    await userService.getUser("123");

    expect(mockLogger.info).toHaveBeenCalledWith("Fetching user 123");
  });
});
```

## Testing Expectations

- Add or update unit tests with the project's framework and naming style
- Expand integration or end-to-end suites when behavior crosses modules or platform APIs
- Run targeted test scripts for quick feedback before submitting
- Avoid brittle timing assertions; prefer fake timers or injected clocks

## Performance & Reliability

- Lazy-load heavy dependencies and dispose them when done
- Defer expensive work until users need it
- Batch or debounce high-frequency events to reduce thrash
- Track resource lifetimes to prevent leaks

## UI & UX Components

- Sanitize user or external content before rendering
- Keep UI layers thin; push heavy logic to services or state managers
- Use messaging or events to decouple UI from business logic

For Preact-specific patterns, see the frontend-expert agent.

## Documentation & Comments

- Add JSDoc to public APIs; include `@remarks` or `@example` when helpful
- Write comments that capture intent, and remove stale notes during refactors
- Update architecture or design docs when introducing significant patterns

````typescript
/**
 * Manages WebSocket connections with automatic reconnection.
 *
 * @remarks
 * Uses exponential backoff for reconnection attempts.
 * Maximum 5 retry attempts before giving up.
 *
 * @example
 * ```typescript
 * const connection = new WebSocketManager('ws://localhost:8000');
 * connection.on('message', (data) => console.log(data));
 * await connection.connect();
 * ```
 */
export class WebSocketManager {
  // ...
}
````

## Instructions Integration

Follow these instruction files when working on TypeScript code:

- [markdown.instructions.md](.github/instructions/markdown.instructions.md) for documentation
- [writing-style.instructions.md](.github/instructions/writing-style.instructions.md) for prose
- [commit-message.instructions.md](.github/instructions/commit-message.instructions.md) for commits

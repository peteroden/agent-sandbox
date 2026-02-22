# Agent Sandbox - Copilot Instructions

This project is an Agent Sandbox for building agent-UI applications with a Preact frontend and Python backend.

## Architecture

```
Frontend (Preact + AG-UI) <--[AG-UI Protocol]--> Backend (FastMCP) <--[MCP]--> LLM
```

- **Frontend**: Preact + TypeScript, Vite, Tailwind CSS, Wouter routing
- **Backend**: Python 3.12+, FastMCP, Pydantic, Azure OpenAI
- **Communication**: AG-UI protocol for frontend-backend, MCP protocol for backend-LLM

## TDD is Mandatory

All code changes must follow Test-Driven Development:

1. **Red**: Write a failing test first
2. **Green**: Write minimum code to pass
3. **Refactor**: Improve while keeping tests green

Never write implementation code without a corresponding test.

## SOLID Principles

Apply SOLID principles throughout:

- Single Responsibility: One reason to change per class/function
- Open/Closed: Extend via composition, not modification
- Liskov Substitution: Subtypes must be substitutable
- Interface Segregation: Focused, minimal interfaces
- Dependency Inversion: Depend on abstractions, use injection

## Code Review is Mandatory

No coding work is considered complete until:

1. Implementation is finished
2. Unit tests pass (`cd frontend && pnpm test --run`, `cd backend && uv run pytest`)
3. E2E tests pass (`cd e2e && pnpm test`)
4. **Self-review using [code-review.instructions.md](instructions/code-review.instructions.md) checklist**
5. All 🔴 CRITICAL and 🟡 IMPORTANT issues resolved
6. 🟢 SUGGESTION items applied or acknowledged

This applies to all code changes, whether implementing new features, fixing bugs, or refactoring.

## Project Structure

```
/workspaces/agent-sandbox/
├── frontend/                    # Preact frontend application
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   ├── hooks/               # Custom Preact hooks
│   │   ├── pages/               # Route page components
│   │   └── services/            # AG-UI client and API services
│   └── test/                    # Vitest tests
├── backend/                     # Python backend (to be created)
│   ├── src/
│   │   └── agent_sandbox/       # Main package
│   │       ├── server.py        # FastMCP server
│   │       ├── tools/           # MCP tool definitions
│   │       ├── models/          # Pydantic models
│   │       └── services/        # Business logic
│   └── tests/                   # pytest tests
├── e2e/                         # Playwright end-to-end tests
│   ├── tests/                   # Test specifications
│   └── helpers/                 # Shared test utilities
└── .github/
    ├── agents/                  # Custom Copilot agents
    ├── instructions/            # Auto-applied instructions
    └── copilot-instructions.md  # This file
```

## Key Technologies

| Component       | Technology   | Documentation                                          |
| --------------- | ------------ | ------------------------------------------------------ |
| Frontend UI     | Preact       | <https://preactjs.com>                                 |
| Agent Protocol  | AG-UI        | <https://docs.ag-ui.com>                               |
| MCP Server      | FastMCP      | <https://gofastmcp.com>                                |
| Data Validation | Pydantic     | <https://docs.pydantic.dev>                            |
| LLM             | Azure OpenAI | <https://learn.microsoft.com/azure/ai-services/openai> |
| E2E Testing     | Playwright   | <https://playwright.dev>                               |

## Environment Variables

### Backend (Azure OpenAI)

```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=your-deployment-name

# LLM provider selection (default: mock)
LLM_PROVIDER=mock    # Options: mock, azure
```

## Custom Agents

Three specialized agents are available:

- **plan**: Orchestrates complex tasks, explores codebase, and delegates to specialists
- **frontend-expert**: Preact, AG-UI, Vite, Tailwind, Vitest specialist
- **backend-expert**: Python, FastMCP, MCP, Azure OpenAI specialist

The **plan** agent automatically invokes `frontend-expert` or `backend-expert` as needed during execution. All agents enforce TDD and SOLID principles.

## Instructions

Auto-applied instructions in `.github/instructions/`:

| File                             | Applies To                                            | Purpose                         |
| -------------------------------- | ----------------------------------------------------- | ------------------------------- |
| `bash.instructions.md`           | `**/*.sh`                                             | Bash scripting conventions      |
| `code-review.instructions.md`    | `**`                                                  | Mandatory code review checklist |
| `commit-message.instructions.md` | Commits                                               | Conventional commit format      |
| `git-merge.instructions.md`      | Git operations                                        | Merge/rebase protocols          |
| `markdown.instructions.md`       | `**/*.md`                                             | Markdown formatting             |
| `prompt-builder.instructions.md` | `**/*.prompt.md, **/*.agent.md, **/*.instructions.md` | Prompt engineering              |
| `python-script.instructions.md`  | `**/*.py`                                             | Python conventions with TDD     |
| `security.instructions.md`       | `*`                                                   | OWASP security practices        |
| `typescript.instructions.md`     | `**/*.ts, **/*.tsx`                                   | TypeScript conventions with TDD |
| `uv-projects.instructions.md`    | `**/*.py, **/*.ipynb`                                 | uv environment management       |
| `writing-style.instructions.md`  | `**/*.md`                                             | Writing style guide             |

## Development Workflow

### Quick Start

```bash
./scripts/dev.sh  # Starts all services with mock LLM
```

All services run with hot reload enabled (uvicorn `--reload` for Python, Vite HMR for frontend).

### Options

| Option            | Description                               |
| ----------------- | ----------------------------------------- |
| `--mock`          | Use mock LLM (fastest, no real responses) |
| `--azure`         | Use Azure OpenAI (requires API keys)      |
| `--backend-only`  | Skip frontend                             |
| `--frontend-only` | Skip backend                              |

### Health Check

```bash
cd backend && uv run python -m agent_sandbox.health
```

### Manual Startup

#### Frontend

```bash
cd frontend
pnpm install
pnpm dev           # Start dev server on port 5173
pnpm test          # Run Vitest tests
pnpm build         # Production build
```

#### Backend

```bash
cd backend
uv sync            # Install dependencies
uv run pytest      # Run tests
LLM_PROVIDER=mock uv run python -m agent_sandbox.server  # Start server
```

#### E2E Tests

```bash
cd e2e
pnpm install       # Install Playwright + Chromium
pnpm test          # Run all E2E tests (auto-starts dev servers)
pnpm test:ui       # Interactive UI mode
pnpm test:debug    # Debug mode with inspector
```

E2E tests use `scripts/dev.sh --mock` via Playwright's `webServer` config and run against Chromium.

## Commit Conventions

Use conventional commits with project-specific scopes:

- `feat(frontend)`: New frontend feature
- `feat(backend)`: New backend feature
- `feat(agui)`: AG-UI protocol changes
- `feat(mcp)`: MCP/FastMCP changes
- `fix(...)`: Bug fixes
- `test(...)`: Test additions/fixes
- `test(e2e)`: End-to-end test changes
- `docs(...)`: Documentation

See [commit-message.instructions.md](.github/instructions/commit-message.instructions.md) for full details.

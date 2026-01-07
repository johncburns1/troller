# Claude Code Development Guide

Development guide for the Troller project - an autonomous GitHub issue resolution system using Temporal workflows and multi-agent AI orchestration.

## Project Overview

**What**: Autonomous AI agents (Planning/Coding/Review) orchestrated by Temporal workflows to automatically implement and complete GitHub issues.

**Architecture**: Hexagonal architecture with Temporal workflows coordinating domain logic through activities and adapters.

**Key Documents**:

- [PRODUCT.md](PRODUCT.md) - Product vision and requirements
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and technical decisions

## Development Workflow

```bash
# Setup (first time)
uv sync

# Development cycle
uv run ruff check --fix && uv run ruff format  # Format and lint
uv run mypy src                                # Type check
uv run pytest                                  # Run tests

# Pre-commit hooks
uv run pre-commit install  # One-time setup
```

## Engineering Standards

**IMPORTANT**: For detailed engineering guidance, use these skills:

- **`engineering:engineering-standards`** - Core principles (simplicity, TDD, hexagonal architecture, SOLID)
- **`engineering:python-engineering`** - Python tooling (uv, ruff, mypy, pytest) and best practices

The skills provide comprehensive guidance on:

- Test-driven development workflow
- Hexagonal architecture patterns with examples
- Type annotation requirements (Python 3.13+ syntax)
- Code organization and project structure
- Testing strategies (unit vs integration)
- Docstring conventions (Google style)

## Code Quality Checklist

Before committing, ensure:

- [ ] All functions have type annotations (Python 3.13+ syntax)
- [ ] Tests written for business logic (TDD approach)
- [ ] Passes: `ruff check`, `ruff format`, `mypy src`, `pytest`
- [ ] Business logic in domain layer (no framework dependencies)
- [ ] Dependencies point inward (hexagonal architecture)

## Key Architectural Patterns

**Hexagonal Architecture** - Domain logic is isolated from infrastructure:

```python
# Domain (pure business logic - no external dependencies)
class Plan:
    def mark_step_complete(self, step_id: str) -> None: ...

# Port (interface)
class PlanRepository(Protocol):
    def save(self, plan: Plan) -> None: ...

# Adapter (infrastructure implementation)
class TemporalPlanRepository:
    def save(self, plan: Plan) -> None:
        # Convert to Temporal state and persist
        ...
```

**Temporal Workflows** - Keep workflows orchestration-only. Business logic lives in domain models, workflows coordinate activities.

## Project Structure

```
src/troller/
├── domain/          # Pure business logic (no framework dependencies)
│   ├── models/      # Domain entities (Plan, PlanStep)
│   └── ports/       # Interface definitions (protocols)
└── worker/          # Temporal infrastructure
    ├── workflows/   # Orchestration (IssueResolutionWorkflow)
    ├── activities/  # Individual operations (fetch_issue, run_planning_agent)
    └── adapters/    # External integrations (GitHubClient, ClaudeClient)
```

**Last Updated**: 2026-01-05

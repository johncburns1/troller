# Claude Code Development Guide

Development guide for the Troller project - an autonomous GitHub issue resolution system using Temporal workflows and multi-agent AI orchestration.

## Project Overview

**What**: Autonomous AI agents (Planning/Coding/Review) orchestrated by Temporal workflows to automatically implement and complete GitHub issues.

**Key Documents**:

- [PRODUCT.md](PRODUCT.md) - Product vision and requirements
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and technical decisions

## Quick Start

```bash
# First-time setup
uv sync

# Development cycle
uv run ruff check --fix  # Lint and auto-fix
uv run ruff format       # Format code
uv run mypy src          # Type check
uv run pytest            # Run tests

# Build
uv build
```

## Project Commands

### Package Management (uv)

```bash
uv sync                # Install dependencies and create venv
uv add <package>       # Add dependency
uv add --dev <package> # Add dev dependency
uv run <command>       # Run command in venv
```

### Code Quality

```bash
uv run ruff check --fix           # Lint with auto-fix
uv run ruff format                # Format code
uv run mypy src                   # Type check
uv run pytest                     # Run all tests
uv run pytest tests/unit          # Run unit tests
uv run pytest -k "pattern"        # Run tests matching pattern
uv run pytest --cov=src           # Run tests with coverage
uv run pre-commit run --all-files # Run pre-commit hooks manually
```

### Pre-commit Setup

```bash
uv run pre-commit install  # Install git hooks (one-time)
```

## Engineering Standards

This project follows established engineering principles and Python-specific practices. Use the following skills for detailed guidance:

### Core Engineering Principles

Invoke skill: `engineering:engineering-standards`

**Key principles**:

- **Simplicity First**: Simple solutions over clever abstractions
- **Test-Driven Development**: Write tests first for business logic
- **Hexagonal Architecture**: Domain → Application → Ports → Adapters → External
- **SOLID Principles**: SRP, DRY, KISS, YAGNI

### Python Tooling & Practices

Invoke skill: `engineering:python-engineering`

**Key practices**:

- **Type annotations**: All functions must have type hints (Python 3.13+ syntax)
- **Modern syntax**: Use `list[str]`, `dict[str, int]`, `str | int` (not legacy typing)
- **Test naming**: `test_<function>_<scenario>_<expected>`
- **Docstrings**: Google style (don't repeat type information from hints)

## Project Structure

```text
troller/
├── src/
│   └── troller/
│       ├── domain/           # Pure business logic
|       ├── worker/
|           ├── workflows/
|           ├── activities/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── pyproject.toml
└── uv.lock
```

## Code Quality Checklist

Before committing:

- [ ] All functions have type annotations
- [ ] Tests written for business logic
- [ ] Passes: `ruff check`, `ruff format`, `mypy src`, `pytest`
- [ ] Business logic in domain layer (no framework dependencies)
- [ ] Dependencies point inward (hexagonal architecture)

## Key Architectural Patterns

**Hexagonal Architecture**: Separate domain logic from infrastructure concerns.

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

**Keep Temporal workflows orchestration-only**: Business logic goes in domain/services, workflows just coordinate activities.

---

For detailed engineering guidance, invoke:

- `engineering:engineering-standards` - Core principles and patterns
- `engineering:python-engineering` - Python tooling and best practices

**Last Updated**: 2025-12-31

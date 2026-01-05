# Troller

Autonomous GitHub issue resolution system using Temporal workflows and multi-agent AI orchestration.

## Overview

Troller automatically implements GitHub issues using AI agents orchestrated by Temporal workflows:
- **Planning Agent** - Analyzes issues and creates implementation plans
- **Coding Agent** - Implements the planned changes
- **Review Agent** - Reviews code quality and completeness

See [PRODUCT.md](PRODUCT.md) for product vision and [ARCHITECTURE.md](ARCHITECTURE.md) for technical design.

## Quick Start

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Code quality
uv run ruff check --fix && uv run ruff format && uv run mypy src
```

## Architecture

Follows **hexagonal architecture** (ports and adapters):
- **Domain** - Pure business logic (no framework dependencies)
- **Workflows** - Temporal orchestration (coordinates activities)
- **Activities** - Individual operations (GitHub API, Claude API calls)
- **Adapters** - Infrastructure implementations

Dependencies point inward: `Domain ← Workflows ← Activities ← Adapters`

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design decisions.

## Testing

```bash
# All tests
uv run pytest

# Specific test types
uv run pytest tests/unit          # Fast, isolated unit tests
uv run pytest tests/integration   # End-to-end workflow tests
```

Integration tests validate the full stack using Temporal's testing framework with mocked APIs.

## Development

For contributors, see [CLAUDE.md](CLAUDE.md) for detailed development guide and engineering standards.

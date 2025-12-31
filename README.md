# Troller

Autonomous GitHub issue resolution system using Temporal workflows and multi-agent AI orchestration.

## Quick Start

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run linting and type checking
uv run ruff check --fix
uv run ruff format
uv run mypy src

# Install pre-commit hooks
uv run pre-commit install
```

## Project Structure

```
troller/
├── src/troller/
│   ├── domain/          # Pure business logic (no external dependencies)
│   │   ├── models/      # Domain entities with business logic
│   │   └── ports/       # Interface definitions (contracts)
│   └── worker/          # Temporal worker infrastructure
│       ├── workflows/   # Orchestration layer (application services)
│       ├── activities/  # Activity implementations
│       └── adapters/    # Infrastructure adapters (repos, APIs)
└── tests/
    ├── unit/            # Fast, isolated tests
    ├── integration/     # Integration tests
    └── fixtures/        # Test fixtures
```

## Architecture

This project follows **hexagonal architecture** (ports and adapters):

- **Domain Models**: Rich entities containing business logic (no external dependencies)
- **Ports**: Interfaces defining contracts (e.g., repositories, external services)
- **Workflows**: Orchestration/application layer coordinating domain logic
- **Activities**: Individual operations called by workflows
- **Adapters**: Infrastructure implementations (Temporal, Anthropic API, GitHub)

**Key Principles**:
- Domain entities are self-contained with their business logic
- Workflows orchestrate domain objects (they don't contain business logic)
- Dependencies point inward: Domain ← Ports ← Adapters
- All business rules live in domain models, workflows just coordinate

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design decisions.
See [PRODUCT.md](PRODUCT.md) for product vision and requirements.

## Development

See [CLAUDE.md](CLAUDE.md) for detailed development guide and engineering standards.

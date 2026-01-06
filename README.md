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

## Configuration

Troller uses environment variables for configuration. Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` to customize your configuration:

```bash
# Temporal server
TEMPORAL_ADDRESS=localhost:7233
TEMPORAL_TASK_QUEUE=troller-task-queue

# GitHub (optional for public repos)
GITHUB_TOKEN=your_token_here

# Logging
LOG_LEVEL=INFO
```

Configuration priority (highest to lowest):

1. Command-line arguments
2. Environment variables
3. `.env` file
4. Default values

## Running the Worker

Start a local Temporal dev server (in a separate terminal):

```bash
temporal server start-dev
```

Start the Troller worker:

```bash
uv run python src/troller/worker/run_worker.py
```

Optional arguments:

- `--temporal-address`: Temporal server address
- `--task-queue`: Task queue name

## Triggering Workflows

Trigger an issue resolution workflow:

```bash
uv run python cli.py \
  --repo-owner <owner> \
  --repo-name <repo> \
  --issue-number <number>
```

Example:

```bash
uv run python cli.py \
  --repo-owner johncburns1 \
  --repo-name troller \
  --issue-number 7
```

Optional arguments:

- `--target-branch`: Target branch for implementation
- `--temporal-address`: Temporal server address
- `--task-queue`: Task queue name

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

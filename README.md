# Troller

Troller is an autonomous GitHub issue resolution system that uses multi-agent AI to automatically implement low-priority issues end-to-end. It orchestrates Planning, Coding, and Review agents through Temporal workflows to analyze issues, generate implementation plans, write code, and iterate based on CI/CD feedback—freeing developers to focus on high-impact work.

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/Nordstrom-Sandbox/amplify-ai-troller.git
cd amplify-ai-troller

# 2. Install dependencies
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys (see Configuration below)

# 4. Start Temporal dev server (in separate terminal)
temporal server start-dev

# 5. Start the worker
uv run python src/troller/worker/run_worker.py

# 6. Trigger a workflow
uv run python cli.py --repo-owner <owner> --repo-name <repo> --issue-number <number>
```

## What It Does

Troller automates the resolution of GitHub issues using a three-agent architecture:

- **Planning Agent (Claude Opus)** - Analyzes issues and creates structured implementation plans
- **Coding Agent (Claude Sonnet)** - Implements the planned changes using Claude Code SDK
- **Review Agent (Claude Sonnet)** - Reviews code quality and adherence to plan

The system creates a feature branch, opens a PR, and iterates based on CI/CD feedback until the work is complete or requires human intervention.

## What You'll Need

- **Python 3.13+** with [uv](https://docs.astral.sh/uv/) package manager
- **Temporal** - Local dev server or Temporal Cloud account
- **GitHub Token** - For repository access and PR management
- **LLM API Access** - Either:
  - Anthropic API key, or
  - AWS Bedrock with Claude model access

## Configuration

Create a `.env` file from the template:

```bash
# Temporal server
TEMPORAL_ADDRESS=localhost:7233
TEMPORAL_TASK_QUEUE=troller-task-queue

# GitHub
GITHUB_TOKEN=your_token_here

# LLM Provider (choose one)
ANTHROPIC_API_KEY=your_api_key_here     # Option 1: Anthropic API

# OR for AWS Bedrock:
CLAUDE_CODE_USE_BEDROCK=1                # Option 2: AWS Bedrock
LLM_BEDROCK_REGION=us-west-2
LLM_BEDROCK_PROFILE=your_profile

# Logging
LOG_LEVEL=INFO
```

> [!todo] Demo
> Demo video and screenshots coming soon.

## Architecture

Follows **hexagonal architecture** (ports and adapters):

- **Domain** - Pure business logic (no framework dependencies)
- **Workflows** - Temporal orchestration (coordinates activities)
- **Activities** - Individual operations (GitHub API, Claude API calls)
- **Adapters** - Infrastructure implementations

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design and [PRODUCT.md](PRODUCT.md) for product vision.

## Development

```bash
# Run tests
uv run pytest

# Code quality
uv run ruff check --fix && uv run ruff format && uv run mypy src
```

For contributors, see [CLAUDE.md](CLAUDE.md) for detailed development guide and engineering standards.

## Documentation

- [ONE-PAGER.md](ONE-PAGER.md) - Project overview and key features
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and technical decisions
- [PRODUCT.md](PRODUCT.md) - Product vision and requirements
- [AI-ASSESSMENT.md](AI-ASSESSMENT.md) - AI capabilities and governance assessment
- [CONTRIBUTORS.md](CONTRIBUTORS.md) - Project contributors

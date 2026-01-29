# Troller - One Pager

## Problem Statement

Development teams accumulate backlogs of low-priority issues (bugs, features, chores, tech debt) that never get addressed because they're not urgent enough to prioritize. These items create technical debt, degrade user experience, and cause mental overhead, but manually working through them is not an efficient use of senior engineering time.

## Solution

Troller is an autonomous AI agent system that automatically implements and completes low-priority GitHub issues end-to-end, freeing developers to focus on high-impact work. It uses specialized AI agents orchestrated by Temporal workflows to analyze issues, generate implementation plans, write code, and iterate based on CI/CD feedback.

## How It Works

```
1. Trigger    Developer triggers workflow with repo + issue number
      |
      v
2. Plan       Planning Agent (Claude Opus) analyzes issue and creates structured plan
      |
      v
3. Implement  Coding Agent (Claude Sonnet) implements changes using Claude Code SDK
      |
      v
4. Review     Review Agent (Claude Sonnet) validates quality and plan adherence
      |
      v
5. Commit     Changes committed to feature branch, PR created/updated
      |
      v
6. CI/CD      Monitor GitHub Actions, categorize failures (code vs environment)
      |
      v
7. Iterate    Code failures -> auto-fix and retry
              Environment failures -> escalate to human with actionable tasks
              Success -> continue to next step or complete
```

**Long-Running Support**: Workflows can run for days, weeks, or months using Temporal's continue-as-new pattern. The system detects existing work and adapts plans to avoid repetition.

## Key Features

- **Multi-Agent Architecture** - Specialized agents (Planning/Coding/Review) with distinct roles and optimal model selection
- **Intelligent Failure Handling** - Distinguishes code failures (auto-retry) from environment failures (human escalation)
- **CI/CD Feedback Loop** - Automatically iterates based on build/test results
- **Resilient State Management** - Long-running workflows with state preservation and work detection
- **Language Agnostic** - Works with any codebase via Claude Code SDK

## Technical Stack

| Component | Technology |
|-----------|------------|
| Workflow Orchestration | Temporal Cloud |
| AI Agents | Claude (Opus for planning, Sonnet for coding/review) |
| Agent Execution | Claude Code SDK |
| GitHub Integration | PyGithub (REST/GraphQL API) |
| Language | Python 3.13+ |
| Architecture | Hexagonal (ports and adapters) |

## Results / Impact

**Target Metrics:**

- 75% autonomous completion rate (workflows complete without human intervention)
- Clear backlog of low-priority issues that would otherwise be indefinitely deferred
- Measurable developer time savings on routine implementation tasks

**Current Status:** Experimental / Proof of Concept

## What's Next

1. **V1 (MVP)** - Single-PR autonomous implementation with full CI/CD feedback loop
2. **V2** - Multi-PR orchestration for complex issues, human-in-the-loop feedback
3. **V3** - Automatic issue selection, analytics dashboard, language-specific optimizations

## Links

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed system design
- [PRODUCT.md](PRODUCT.md) - Full product requirements
- [AI-ASSESSMENT.md](AI-ASSESSMENT.md) - AI governance assessment

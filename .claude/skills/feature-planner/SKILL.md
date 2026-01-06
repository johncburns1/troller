---
name: feature-planner
description: Planning workflow for GitHub issues - explores codebase, analyzes requirements, invokes engineering standards, and creates implementation plan. Use when starting work on an issue or feature.
allowed-tools: Task, TodoWrite, Bash(git:*), Bash(gh:*), Skill(engineering:engineering-standards), Skill(engineering:python-engineering)
---

# Feature Planner

Creates implementation plans for GitHub issues with YAGNI validation.

## When to Use

- Starting work on a GitHub issue
- Before implementing features or bug fixes

## Planning Workflow

### 1. Fetch & Understand Issue

```bash
gh issue view <issue-number>
```

Identify acceptance criteria, dependencies, affected components.

### 2. YAGNI Check - Is Work Actually Needed?

**Before planning implementation, audit the current state:**

```text
Task(subagent_type="Explore", thoroughness="very thorough"):
"Audit current implementation related to issue #<number>.
Determine if the problem described actually exists.
Find [specific components mentioned in issue].
Check if functionality already works as described."
```

**Decision point:**
- **If issue is already resolved or doesn't apply:** Report findings, recommend closing issue
- **If work is needed:** Continue to step 3

### 3. Deep Codebase Analysis

```text
Task(subagent_type="Explore", thoroughness="very thorough"):
"Analyze codebase for implementing [feature/fix].
Find related files, existing patterns, test strategies, and similar implementations.
Identify architecture patterns being followed."
```

### 4. Apply Engineering Standards

```text
Skill(engineering:engineering-standards)
Skill(engineering:python-engineering)  # For Python projects
```

### 5. Create Branch & Plan

**Create feature branch:**

```bash
git checkout -b feature/issue-<number>-<brief-description>
```

**Create detailed TodoWrite plan:**

```text
TodoWrite([
  {content: "Write tests for [specific component]", status: "pending", activeForm: "Writing tests"},
  {content: "Implement [component 1]", status: "pending", activeForm: "Implementing [component 1]"},
  {content: "Implement [component 2]", status: "pending", activeForm: "Implementing [component 2]"},
  {content: "Update existing tests", status: "pending", activeForm: "Updating tests"},
  {content: "Run quality checks (ruff, mypy, pytest)", status: "pending", activeForm: "Running quality checks"},
  {content: "Commit and push", status: "pending", activeForm: "Committing changes"},
  {content: "Create pull request", status: "pending", activeForm: "Creating PR"}
])
```

**Requirements:**
- Break down into specific, testable tasks
- Test tasks come BEFORE implementation tasks (TDD)
- Include quality checks as explicit step

## Planning Output

Present to user:
- ✅ YAGNI validation result
- ✅ Branch created (if work needed)
- ✅ TodoWrite plan with specific tasks
- ✅ Understanding of existing patterns
- ✅ Architecture approach

## Handoff to Implementation

Once user confirms plan, use `feature-implementation` skill to execute.

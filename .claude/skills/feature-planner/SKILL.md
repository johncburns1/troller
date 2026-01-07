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

### 2. YAGNI Validation & Codebase Analysis (Combined)

**Single exploration pass that validates need and gathers context:**

```text
Task(subagent_type="Explore", thoroughness="medium"):
"Explore codebase for issue #<number>: [brief issue description]

FIRST: Validate if work is needed
- Find [specific components mentioned in issue]
- Check if the problem/feature described actually exists or is already implemented
- Determine if issue is valid or can be closed

IF work is needed:
- Find related files and existing patterns
- Identify test strategies and similar implementations
- Note architecture patterns being followed
- Locate where changes should be made

Return both YAGNI validation and implementation context."
```

**Decision point:**

- **If issue is already resolved or doesn't apply:** Report findings, recommend closing issue
- **If work is needed:** Continue to step 3 (you already have the context)

### 3. Apply Engineering Standards

```text
Skill(engineering:engineering-standards)
Skill(engineering:python-engineering)  # For Python projects
```

### 4. Plan

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

### 5. Validate Plan

Before presenting:

- YAGNI audit: remove speculative/future work from plan
- Flag unused code/fields found during exploration
- Document assumptions

## Planning Output

- YAGNI validation (proceed/skip + reason)
- Branch created
- TodoWrite plan
- **Specific files to modify** (with paths for implementation)
- Key patterns/architecture
- Assumptions/dead code (if any)

## Handoff to Implementation

Once user confirms plan, use `feature-implementation` skill to execute.

**CRITICAL:** List exact file paths for implementation agent to read.

---
name: feature-planner
description: Planning workflow for GitHub issues - explores codebase, analyzes requirements, invokes engineering standards, and creates implementation plan. Use when starting work on an issue or feature.
allowed-tools: Task, TodoWrite, Bash(git:*), Bash(gh:*), Skill(engineering:engineering-standards), Skill(engineering:python-engineering)
---

# Feature Planner

Creates comprehensive implementation plans for GitHub issues.

## When to Use

- Starting work on a GitHub issue
- Need to understand requirements and plan approach
- Before implementing features or bug fixes

## Planning Steps

### 1. Discover & Analyze

**Fetch issue:**

```bash
gh issue view <issue-number>
```

**Identify:**

- Acceptance criteria
- Dependencies
- Affected components
- Technical constraints

**Explore codebase thoroughly:**

```text
Task(subagent_type="Explore", thoroughness="very thorough"):
"Analyze codebase structure and architecture.
Find files related to [feature/component].
Identify existing patterns, testing strategies, and similar implementations."
```

### 2. Apply Standards & Create Plan

**Invoke engineering standards:**

```text
Skill(engineering:engineering-standards)
Skill(engineering:python-engineering)  # For Python projects
```

**Create branch:**

```bash
git checkout -b feature/issue-<number>-<description>
```

**Create implementation plan with TodoWrite:**

```text
TodoWrite([
  {content: "Implement [component 1]", status: "pending", activeForm: "Implementing [component 1]"},
  {content: "Implement [component 2]", status: "pending", activeForm: "Implementing [component 2]"},
  {content: "Write tests", status: "pending", activeForm: "Writing tests"},
  {content: "Quality checks passing", status: "pending", activeForm: "Running checks"},
  {content: "Commit and push", status: "pending", activeForm: "Pushing changes"},
  {content: "Create pull request", status: "pending", activeForm: "Creating PR"}
])
```

Break down into specific, actionable tasks.

## Output

After planning, provide:

- ✅ Branch created
- ✅ TodoWrite checklist created
- ✅ Engineering standards applied
- ✅ Understanding of existing patterns
- ✅ Clear implementation steps

## Handoff to Implementation

Once planning is complete, use the `feature-implementation` skill to execute the plan.

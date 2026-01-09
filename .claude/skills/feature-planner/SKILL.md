---
name: feature-planner
description: Planning workflow for GitHub issues - explores codebase, analyzes requirements, and creates TDD-structured implementation plans with granular substeps.
allowed-tools: Task, TodoWrite, Bash(git:*), Bash(gh:*), Skill(engineering:engineering-standards), Skill(engineering:python-engineering)
---

# Feature Planner

Creates TDD-structured implementation plans for GitHub issues with YAGNI validation.

## When to Use

- Starting work on a GitHub issue
- Before implementing features or bug fixes

## Planning Workflow

### 1. Fetch & Understand Issue

```bash
gh issue view <issue-number>
```

Identify acceptance criteria, dependencies, affected components.

### 2. YAGNI Validation & Codebase Analysis

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
- If issue is already resolved: Report findings, recommend closing
- If work is needed: Continue to step 3

### 3. Apply Engineering Standards

```text
Skill(engineering:engineering-standards)
Skill(engineering:python-engineering)
```

### 4. Create TDD-Structured Plan

For each logical unit of work, create a step with TDD substeps:

**Step Structure:**
```json
{
  "id": "step-1",
  "description": "Implement [specific feature]",
  "related_files": ["exact/paths/to/files.py"],
  "estimated_complexity": "simple|moderate|complex",
  "substeps": [
    {
      "id": "step-1.1",
      "phase": "write_test",
      "description": "Write failing test for [behavior]",
      "file_operations": [{
        "operation": "create|modify",
        "file_path": "tests/path/test_file.py",
        "description": "Create test",
        "code_snippet": "def test_behavior():\n    assert function() == expected"
      }],
      "verification": {
        "command": "uv run pytest tests/path/test_file.py::test_behavior -v",
        "expected_outcome": "fail",
        "expected_text": "FAILED"
      }
    },
    {
      "id": "step-1.2",
      "phase": "implement",
      "description": "Implement minimal code to pass test",
      "file_operations": [{
        "operation": "create|modify",
        "file_path": "src/path/module.py",
        "description": "Add implementation",
        "code_snippet": "def function():\n    return expected"
      }],
      "verification": {
        "command": "uv run pytest tests/path/test_file.py::test_behavior -v",
        "expected_outcome": "pass",
        "expected_text": "1 passed"
      }
    },
    {
      "id": "step-1.3",
      "phase": "verify_passes",
      "description": "Run full quality checks",
      "verification": {
        "command": "uv run ruff check && uv run mypy src && uv run pytest",
        "expected_outcome": "pass"
      }
    }
  ],
  "commit_message_template": "feat(scope): add specific feature"
}
```

**Requirements:**
- Each step is a commit-worthy unit with complete TDD cycle
- Test tasks come BEFORE implementation (TDD)
- Include exact file paths and code snippets
- Include verification commands with expected outcomes
- Break complex features into multiple steps

### 5. Validate Plan

Before returning:
- YAGNI audit: remove speculative/future work
- Verify all file paths exist or will be created
- Ensure each step has clear verification criteria
- Document assumptions

## Planning Output Schema

Return structured JSON matching this schema:

```json
{
  "summary": "High-level description",
  "steps": [/* PlanStepResponse objects with substeps */],
  "technical_approach": "Architecture decisions",
  "testing_strategy": "Testing approach"
}
```

## Key Principles

- **Bite-sized substeps**: Each substep is 2-5 minutes of work
- **TDD cycle**: write_test -> verify_fails -> implement -> verify_passes -> commit
- **Exact paths**: Full file paths, not relative or vague
- **Code snippets**: Actual code, not descriptions like "add validation"
- **Verification**: Every substep has a command to verify success
- **Atomic commits**: Each step produces one clean commit

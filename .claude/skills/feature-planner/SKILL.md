---
name: feature-planner
description: Creates TDD-structured implementation plans for GitHub issues with YAGNI validation and granular substeps.
allowed-tools: Task, TodoWrite, Bash(git:*), Bash(gh:*), Skill(engineering:engineering-standards), Skill(engineering:python-engineering)
---

# Feature Planner

## Workflow

### 1. Understand Issue

```bash
gh issue view <issue-number>
```

### 2. YAGNI Check & Codebase Analysis

```
Task(subagent_type="Explore", thoroughness="medium"):
"For issue #<N>: [description]
- Does this already exist? Can issue be closed?
- If work needed: find related files, patterns, test strategies"
```

**Stop here if issue is invalid or already resolved.**

### 3. Create Feature Branch

```bash
git checkout -b feature/<issue-number>-<short-description>
```

### 4. Apply Standards

```
Skill(engineering:engineering-standards)
Skill(engineering:python-engineering)
```

### 5. Generate Plan

Each step follows **Red-Green-Refactor** with verification:

```json
{
  "summary": "What this plan accomplishes",
  "technical_approach": "Architecture decisions",
  "testing_strategy": "Unit tests per step, integration test at end",
  "steps": [
    {
      "id": "step-1",
      "description": "Add user validation",
      "depends_on": [],
      "related_files": ["src/auth/validator.py", "tests/auth/test_validator.py"],
      "estimated_complexity": "moderate",
      "substeps": [
        {
          "id": "step-1.1",
          "phase": "write_test",
          "description": "Write failing test for email validation",
          "file_operations": [{
            "operation": "create",
            "file_path": "tests/auth/test_validator.py",
            "code_snippet": "def test_validates_email():\n    assert validate_email('bad') is False"
          }],
          "verification": {
            "command": "uv run pytest tests/auth/test_validator.py::test_validates_email -v",
            "expected_outcome": "fail"
          }
        },
        {
          "id": "step-1.2",
          "phase": "implement",
          "description": "Implement minimal validation",
          "file_operations": [{
            "operation": "create",
            "file_path": "src/auth/validator.py",
            "code_snippet": "def validate_email(email: str) -> bool:\n    return '@' in email"
          }],
          "verification": {
            "command": "uv run pytest tests/auth/test_validator.py::test_validates_email -v",
            "expected_outcome": "pass"
          }
        },
        {
          "id": "step-1.3",
          "phase": "refactor",
          "description": "Clean up if needed, run full checks",
          "verification": {
            "command": "uv run ruff check && uv run mypy src && uv run pytest",
            "expected_outcome": "pass"
          }
        }
      ],
      "commit_message_template": "feat(auth): add email validation"
    },
    {
      "id": "step-2",
      "description": "Integration test",
      "depends_on": ["step-1"],
      "related_files": ["tests/integration/test_auth_flow.py"],
      "estimated_complexity": "simple",
      "substeps": [
        {
          "id": "step-2.1",
          "phase": "write_test",
          "description": "Add integration test for full auth flow",
          "file_operations": [{
            "operation": "modify",
            "file_path": "tests/integration/test_auth_flow.py",
            "code_snippet": "def test_auth_validates_email(): ..."
          }],
          "verification": {
            "command": "uv run pytest tests/integration/ -v",
            "expected_outcome": "pass"
          }
        }
      ],
      "commit_message_template": "test(auth): add integration test"
    }
  ]
}
```

## On Verification Failure

- **Test fails to fail (write_test)**: Feature may already exist, or test is wrong
- **Implementation fails (implement)**: Debug before proceeding, don't skip
- **Quality checks fail (refactor)**: Fix all issues before commit

## Handoff

Plan complete. Execute with `Skill(feature-implementation)`.

## Principles

- **TDD**: write_test (red) -> implement (green) -> refactor
- **Atomic commits**: Each step = one commit
- **Exact paths & code**: No vague descriptions
- **Verification at every step**: Commands with expected outcomes
- **Dependencies explicit**: `depends_on` for step ordering
- **Integration tests last**: Unit tests per step, integration at end

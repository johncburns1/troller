---
name: feature-implementation
description: TDD implementation with quality gates - loads standards, iterates until tests pass, commits changes.
allowed-tools: Task, TodoWrite, Bash(git status:*), Bash(git diff:*), Bash(git restore:*), Bash(uv:*), Bash(pytest:*), Bash(ruff:*), Bash(mypy:*), Skill(engineering:engineering-standards), Skill(engineering:python-engineering), Skill(commit-commands:commit), Skill(commit-commands:commit-push-pr), Read, Write, Edit
---

# Feature Implementation

TDD-based implementation with iterative quality gates.

## Workflow

### 1. Read Specific Files from Plan

**IMPORTANT:** Only read files explicitly identified by the planner. Do NOT perform broad codebase exploration.

```bash
# Read ONLY the specific files called out in the plan
Read(file_path="/path/to/file.py")
Read(file_path="/path/to/test_file.py")
```

Trust the planning exploration - you have all the context you need.

### 2. Load Engineering Standards

Load BEFORE implementation starts to prime TDD/architecture context:

```text
Skill(engineering:engineering-standards)
Skill(engineering:python-engineering)
```

### 3. Implement with TDD (Max 5 iterations)

Follow TDD approach with explicit iteration:

**For each iteration (max 5):**

1. **Write/update tests FIRST** (TDD principle)
   - Create test file if needed
   - Write failing tests for the feature
   - Tests should cover the requirements from the plan

2. **Implement code to pass tests**
   - Modify/create source files
   - Follow hexagonal architecture patterns
   - Keep changes focused on the task

3. **Run quality checks:**
   ```bash
   uv run pytest
   uv run ruff check --fix
   uv run ruff format
   uv run mypy src
   ```

4. **Evaluate results:**
   - ALL PASS → Exit loop, proceed to Step 4
   - ANY FAIL → Analyze errors, fix, continue iteration

**Exit Conditions:**
- All quality checks pass → Success, proceed to Final QA
- Max iterations (5) reached → Document blockers, proceed with best effort
- Same error 3+ times → Simplify approach or break into smaller tasks

**Progress Tracking:**
- Update TodoWrite after each iteration
- Mark subtasks as completed when verified
- One task in_progress at a time

**Troubleshooting:**
- If stuck on same error: Check assumptions, read related code
- If tests won't pass: Verify test logic first, then implementation
- If type errors persist: Check imports and type annotations

### 4. Final QA

```bash
uv run pytest && uv run ruff check --fix && uv run ruff format && uv run mypy src
```

**Validate before commit:**

- All TodoWrite tasks completed
- No unrelated changes (git diff)
- Remove dead code

### 5. Commit, Push, and Create PR

**Before committing, verify changes:**

```bash
git status                        # Review all changes
git diff                          # Check for unrelated changes
git restore <unrelated-file>      # Clean up any unrelated files
```

> **Note (Autonomous Mode):** When running via Troller's implementation service, skip committing - the service handles git operations after this skill completes. Just ensure changes are clean and tests pass.

**Option A: Commit, push, and PR in one step** (interactive use)

```text
Skill(commit-commands:commit-push-pr)
```

This will:

- Create new branch if on main
- Stage and commit all changes
- Push to origin
- Create pull request

**Option B: Just commit** (interactive use)

```text
Skill(commit-commands:commit)
```

Then manually push and create PR later.

**The commit command will automatically:**

- Review git status and diff
- Create appropriate commit message following project conventions
- Include issue references and acceptance criteria

Complete TodoWrite.

## Rules

- Only modify files related to the task
- Update TodoWrite frequently (in_progress → completed)
- One task in_progress at a time
- Fix quality check failures immediately

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Tests failing repeatedly | Check test logic before implementation |
| Type errors persist | Verify imports and annotations match |
| Max iterations reached | Simplify task or document blockers |
| Unrelated changes | `git restore <file>` |

---
name: feature-implementation
description: Ralph Wiggum TDD loops - loads engineering standards, iterates with quality gates, commits, creates PR.
allowed-tools: Task, TodoWrite, Bash(git status:*), Bash(git diff:*), Bash(git restore:*), Bash(uv:*), Bash(pytest:*), Bash(ruff:*), Bash(mypy:*), Skill(engineering:engineering-standards), Skill(engineering:python-engineering), Skill(ralph-loop:ralph-loop), Skill(commit-commands:commit), Skill(commit-commands:commit-push-pr), Read, Write, Edit
---

# Feature Implementation

Ralph Wiggum iteration loops with TDD and quality gates.

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

Load BEFORE Ralph Wiggum starts to prime TDD/architecture context:

```text
Skill(engineering:engineering-standards)
Skill(engineering:python-engineering)
```

### 3. Run Ralph Loop

The Ralph Loop requires a task description from the plan. Format:

```text
Skill(ralph-loop:ralph-loop, args="[TASK_DESCRIPTION] --max-iterations 5 --completion-promise 'TASK COMPLETE'")
```

**Example:**

```text
Skill(ralph-loop:ralph-loop, args="Implement user authentication with JWT tokens --max-iterations 5 --completion-promise 'All tests passing'")
```

**IMPORTANT:** Replace `[TASK_DESCRIPTION]` with your feature implementation plan (from the planner).

**Arguments:**

- `[TASK_DESCRIPTION]` - Required: Clear description of what to implement
- `--max-iterations N` - Optional: Max iterations (default: unlimited)
- `--completion-promise 'TEXT'` - Optional: Exit phrase (must use quotes for multi-word)

Ralph Loop iterates automatically:

- Read code
- Write tests first (TDD)
- Implement to pass tests
- Run quality checks: pytest, ruff, mypy
- Fix issues
- Repeat

**Exit conditions:**

- Max iterations reached
- Completion promise detected in output
- Early exit if all checks pass

**Update TodoWrite as tasks complete.**

**Troubleshooting loops:**

- If stuck (same errors 2+ times): simplify approach
- If max iterations reached: review assumptions, consider breaking down task

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

**Option A: Commit, push, and PR in one step**

```text
Skill(commit-commands:commit-push-pr)
```

This will:

- Create new branch if on main
- Stage and commit all changes
- Push to origin
- Create pull request

**Option B: Just commit (if you want to review before pushing)**

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
| Ralph loop permission error | Ensure task description is provided in args |
| Max iterations exceeded | Simplify or break into smaller tasks |
| Unrelated changes | `git restore <file>` |

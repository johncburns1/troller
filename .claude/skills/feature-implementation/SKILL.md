---
name: feature-implementation
description: Ralph Wiggum TDD loops - loads engineering standards, iterates with quality gates, commits, creates PR.
allowed-tools: Task, TodoWrite, Bash(git:*), Bash(gh:*), Bash(uv:*), Bash(pytest:*), Bash(ruff:*), Bash(mypy:*), Skill(engineering:engineering-standards), Skill(engineering:python-engineering), Skill(ralph-wiggum:ralph-loop), Read, Write, Edit
---

# Feature Implementation

Ralph Wiggum iteration loops with TDD and quality gates.

## Workflow

### 1. Read Existing Code

```bash
Read(file_path="/path/to/file.py")
Read(file_path="/path/to/test_file.py")
```

### 2. Load Engineering Standards

Load BEFORE Ralph Wiggum starts to prime TDD/architecture context:

```text
Skill(engineering:engineering-standards)
Skill(engineering:python-engineering)
```

### 3. Run Ralph Wiggum Loop

```text
Skill(ralph-wiggum:ralph-loop, args="5")
```

**If permission error:** Request user approval, don't skip.

Ralph Wiggum iterates automatically (max 5):

- Read code
- Write tests first (TDD)
- Implement to pass tests
- Run quality checks: pytest, ruff, mypy
- Fix issues
- Repeat

**Update TodoWrite as tasks complete.**

**Early termination:**
- Exit early if tests + quality checks pass
- If stuck (same errors 2+ times): simplify approach
- If max iterations: review assumptions, break down task

### 4. Final QA

```bash
uv run pytest && uv run ruff check --fix && uv run ruff format && uv run mypy src
```

**Validate before commit:**
- All TodoWrite tasks completed
- No unrelated changes (git diff)
- Remove dead code

### 5. Clean Commit

```bash
git status
git diff                          # Check for unrelated changes
git restore <unrelated-file>      # Clean up
git add <relevant-files>
git commit -m "$(cat <<'EOF'
<Summary ≤50 chars>

Technical details:
- Created/modified [files]
- [Architecture decisions]

Acceptance criteria:
✓ [Criteria from issue]
✓ Tests pass ([N] tests)
✓ Quality checks pass

Closes #<issue-number>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

### 6. Push & PR

```bash
git push -u origin <branch-name>
gh pr create --title "Title" --body "$(cat <<'EOF'
## Summary
[What and why]

## Changes
- Created/modified [files and purpose]

## Testing
✓ [N] tests passing
✓ Quality checks passing

## Acceptance Criteria
✓ [Criteria from issue]

Closes #<issue-number>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Complete TodoWrite.

## Rules

- Only modify files related to the task
- Update TodoWrite frequently (in_progress → completed)
- One task in_progress at a time
- Fix quality check failures immediately

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Ralph Wiggum permission error | Request user approval |
| Max iterations exceeded | Simplify or break into smaller tasks |
| Unrelated changes | `git restore <file>` |

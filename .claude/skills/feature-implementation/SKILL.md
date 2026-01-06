---
name: feature-implementation
description: Implementation workflow using iteration loops - explores repository to prime context, invokes engineering standards, implements changes with Ralph-wiggum (max iterations), runs quality checks, commits, and creates PR. Use when executing an implementation plan.
allowed-tools: Task, TodoWrite, Bash(git:*), Bash(gh:*), Bash(uv:*), Bash(pytest:*), Bash(ruff:*), Bash(mypy:*), Skill(engineering:engineering-standards), Skill(engineering:python-engineering)
---

# Feature Implementation

Executes implementation plans using iteration loops with quality gates.

## When to Use

- Have an existing TodoWrite plan to implement
- Ready to write code after planning phase
- Need to implement, test, and create PR

## Implementation Steps

### 1. Prime Context

**Quick exploration:**

```text
Task(subagent_type="Explore", thoroughness="quick"):
"Quick overview of [components being modified].
Review existing patterns and test structure."
```

**Invoke engineering standards:**

```text
Skill(engineering:engineering-standards)
Skill(engineering:python-engineering)  # For Python projects
```

### 2. Implement with Iteration Loops

**Use Ralph-wiggum for implementation (max 3-5 iterations):**

Set max iterations: **5**

Each iteration:

1. **Read** existing code
2. **Implement** following engineering standards
3. **Test** immediately
4. **Quality check** (ruff, mypy, linting)
5. **Fix** issues
6. **Repeat** until passing

**Quality gates:**

- ✅ Tests passing
- ✅ Linting passing (ruff check --fix)
- ✅ Formatting passing (ruff format)
- ✅ Type checking passing (mypy src)

**If max iterations exceeded:** Stop, reassess, simplify approach.

### 3. Final Quality Assurance

```bash
uv run pytest                    # All tests
uv run ruff check --fix          # Linting
uv run ruff format               # Formatting
uv run mypy src                  # Type checking
```

All must pass.

### 4. Commit & Push

**Review:**

```bash
git status
git diff
```

**Commit:**

```bash
git add <files>
git commit -m "$(cat <<'EOF'
<Summary ≤50 chars>

<Detailed description>

Technical details:
- Detail 1
- Detail 2

Acceptance criteria:
✓ Criterion 1
✓ Criterion 2

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

**Push:**

```bash
git push -u origin <branch-name>
```

### 5. Create Pull Request

```bash
gh pr create --title "Title" --body "$(cat <<'EOF'
## Summary
<What was implemented>

## Changes
- Change 1
- Change 2

## Testing
✓ All tests passing
✓ Quality checks passing

## Acceptance Criteria
✓ All criteria met

Closes #<issue-number>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**Complete TodoWrite.**

## Quick Checklist

```markdown
- [ ] Quick exploration (Task/Explore)
- [ ] Invoke engineering standards
- [ ] Implement with Ralph-wiggum (max 5 iterations)
  - [ ] Read → Code → Test → Fix → Repeat
- [ ] Final QA (all checks passing)
- [ ] Commit
- [ ] Push
- [ ] Create PR
- [ ] Complete TodoWrite
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Max iterations hit | Simplify, break into smaller tasks |
| Tests failing | Fix before committing |
| Pre-commit fails | Add deps to `.pre-commit-config.yaml` |

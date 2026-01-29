# AI Design Review Assessment

This document contains the AI design review assessment for Troller, an autonomous GitHub issue resolution system.

## Applicability Determination

**Does this project contain AI or use a 3rd party vendor product that uses AI?**

**Yes.** Troller uses Claude AI models (via Anthropic API or AWS Bedrock) for autonomous code generation, planning, and review.

### Applicable Sections

| Section | Name | Required? | Reason |
|---------|------|-----------|--------|
| 2 | Core AI Architecture & Integration | Yes | Uses Claude API for multi-agent orchestration |
| 3 | In-House Model Development | No | No custom model training or fine-tuning |
| 4 | Generative AI Specifics | Yes | Uses generative AI (Claude) for code generation |
| 5 | MLOps & Production Review | No | Experimental/POC - not deployed to production |

---

## Section 2: Core AI Architecture & Integration

### 2.1 Basic AI Usage Info

**How and why is AI being used in your application?**

Troller uses Claude AI models to autonomously resolve GitHub issues. Three specialized agents coordinate through Temporal workflows:

- **Planning Agent (Claude Opus)**: Analyzes GitHub issues and generates structured implementation plans
- **Coding Agent (Claude Sonnet)**: Implements code changes based on the plan using Claude Code SDK
- **Review Agent (Claude Sonnet)**: Reviews code quality and adherence to the plan

**Business problems addressed:**

- Backlog of low-priority issues that never get prioritized
- Developer time spent on routine implementation tasks
- Technical debt accumulation from deferred work

**Justification for AI:**

- Code implementation requires understanding natural language requirements, existing codebase context, and programming best practices
- Traditional automation cannot handle the variability of issue descriptions and codebase structures
- Claude's code generation capabilities enable end-to-end autonomous implementation

### 2.2 AI Output Usage

**How are AI outputs consumed by systems or users?**

| Output Type | Consumer | Usage |
|-------------|----------|-------|
| Implementation Plans | Coding Agent, Temporal Workflow | Guides code implementation, tracks progress |
| Code Changes | Git Repository, GitHub PR | Committed to feature branches, reviewed via PRs |
| Review Feedback | Coding Agent (internal) | Applied to improve code quality before commit |
| PR Updates | Developers | Communicate implementation status and blockers |
| Failure Categorization | Workflow Logic | Determines retry vs escalation strategy |

**Decision processes:**

- Workflow continues or escalates based on AI-categorized failure types
- Code is committed only after Review Agent approval
- Human intervention requested only for environment-level blockers

### 2.3 Data Scope & Volume

**What is the scale of data processed?**

| Metric | Volume | Notes |
|--------|--------|-------|
| Issues processed | 1-10 per day | Experimental phase |
| LLM API calls per workflow | 10-100+ | Varies by issue complexity |
| Tokens per workflow | ~50K-500K | Planning uses fewer, coding uses more |
| Concurrent workflows | 1-5 | POC scale |

**Data types processed:**

- GitHub issue descriptions and comments
- Source code from target repositories
- CI/CD logs and error messages
- Git commit history and diffs

### 2.4 Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Temporal Workflow                           │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  Fetch   │───▶│ Planning │───▶│  Coding  │───▶│  Review  │  │
│  │  Issue   │    │  Agent   │    │  Agent   │    │  Agent   │  │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘  │
│       │               │               │               │         │
└───────┼───────────────┼───────────────┼───────────────┼─────────┘
        │               │               │               │
        ▼               ▼               ▼               ▼
   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
   │ GitHub  │    │ Claude  │    │ Claude  │    │ Claude  │
   │   API   │    │   API   │    │   API   │    │   API   │
   └─────────┘    └─────────┘    └─────────┘    └─────────┘
```

**Data flow:**

1. Issue data fetched from GitHub API
2. Issue context sent to Claude API (Planning Agent)
3. Plan + codebase context sent to Claude API (Coding Agent)
4. Code changes sent to Claude API (Review Agent)
5. Final code committed to GitHub via Git operations
6. CI/CD status polled from GitHub Actions API

### 2.5 Prediction Cadence & Patterns

**Are AI predictions real-time or batch-processed?**

| Pattern | Description |
|---------|-------------|
| Type | Asynchronous, event-driven |
| Trigger | Manual workflow invocation per issue |
| Duration | Minutes to hours per workflow iteration |
| Latency Requirements | None - long-running workflows acceptable |

**Workflow timing:**

- Workflows run continuously until completion or blocker
- CI/CD polling every 5 minutes
- Continue-as-new triggered every 24 hours for history management
- Total workflow duration: hours to weeks depending on issue complexity

### 2.6 AI Resilience & Fallback Plan

**How does the application handle AI component failures?**

| Failure Type | Detection | Fallback |
|--------------|-----------|----------|
| Claude API timeout | Temporal activity timeout (10-20 min) | Retry with exponential backoff |
| Claude API rate limit (429) | HTTP response code | Limited retries, then pause workflow |
| Invalid AI output | Schema validation | Retry with modified prompt |
| Code failures (build/test) | CI/CD status | Coding agent attempts fix |
| Environment failures | CI/CD log analysis | Escalate to human via PR comment |
| Repeated failures | Failure counter | Escalate after N attempts |

**Escalation path:**

- All unrecoverable failures result in PR update with actionable human tasks
- Workflow pauses and awaits human intervention
- No silent failures - all states are tracked in Temporal history

### 2.7 AI-Specific Security & Privacy

**What security and privacy considerations are unique to the AI implementation?**

| Concern | Mitigation |
|---------|------------|
| Code exposure to LLM | Only processes repositories developer has access to |
| Secrets in code | Relies on repo's existing .gitignore and secret scanning |
| PII in issues | No customer PII expected in issue descriptions |
| API key security | Keys stored in environment variables, not in workflow state |
| Model prompt injection | Structured prompts, code validation before commit |

**Data classification:**

- Internal tool only - processes internal/sandbox repositories
- No customer data or PII sent to Claude API
- Uses approved Claude API endpoints (Anthropic or AWS Bedrock)

### 2.8 AI Output Validation

**How do you ensure AI outputs meet business requirements?**

| Validation Layer | Method |
|------------------|--------|
| Plan validation | Structured JSON schema output |
| Code review | Review Agent evaluates before commit |
| Syntax validation | Implicit via CI/CD build step |
| Test validation | CI/CD test suite must pass |
| Human oversight | All changes visible in PR for human review before merge |

**Quality thresholds:**

- Code must pass CI/CD pipeline (build, test, lint)
- Review Agent must approve code quality
- Human final approval required for PR merge

### 2.9 AI Component Ownership

| Role | Owner | Responsibilities |
|------|-------|------------------|
| Project Lead | Jack Burns | Overall system design, development, operations |
| Data Owner | Jack Burns | Repository access, issue selection |
| Model Owner | Anthropic | Claude model maintenance and updates |
| Domain Expert | Jack Burns | Code quality standards, review criteria |

### 2.10 AI Extensions (MCP) Usage

**Does this project implement or integrate Model Context Protocol (MCP) servers?**

**No.** This project uses the Claude API directly via the Claude Code SDK without MCP server integration.

---

## Section 4: Generative AI Specifics

### 4.1 Hallucination Risk & Mitigation

**How do you minimize and handle potential AI hallucinations?**

| Strategy | Implementation |
|----------|----------------|
| Structured prompts | Agents receive specific instructions with schema constraints |
| Grounded context | All code generation based on actual repository content |
| Multi-agent review | Review Agent validates Coding Agent outputs |
| CI/CD validation | Build/test failures catch incorrect implementations |
| Limited creativity | Agents follow explicit plans rather than inventing approaches |

**Sampling parameters:**

- Using default Claude parameters optimized for code generation
- Structured output (JSON schema) for plan generation
- Temperature not explicitly tuned (using SDK defaults)

### 4.2 Generative AI Disclaimer

**How are users informed about AI-generated content?**

| Context | Disclaimer |
|---------|------------|
| PR description | Indicates AI-generated implementation |
| Commit messages | Include AI generation attribution |
| User awareness | Internal tool - users explicitly trigger AI workflows |

**Note:** This is an internal developer tool. Users trigger the workflow intentionally and understand they are using AI-powered automation.

### 4.3 Ethical & Bias Checks

**What processes review AI outputs for bias or inappropriate content?**

| Check | Implementation |
|-------|----------------|
| Code review | Review Agent checks for quality issues |
| CI/CD pipeline | Automated linting and testing |
| Human review | All PRs require human approval before merge |
| Escalation | Problematic outputs result in workflow pause |

**Testing procedures:**

- Review Agent applies consistent quality criteria
- CI/CD catches code-level issues automatically
- Human reviewer makes final merge decision

### 4.4 Regular Review Cadence

**How often do you reevaluate generative AI outputs for quality?**

| Review Type | Cadence |
|-------------|---------|
| Per-commit review | Every commit (Review Agent) |
| Per-workflow review | Human reviews PR before merge |
| System-level review | As needed during experimental phase |

**Responsible parties:**

- Automated: Review Agent, CI/CD pipeline
- Manual: Developer reviewing PRs (Jack Burns for POC)

### 4.5 Prompt & Data Security/Privacy

**What privacy safeguards exist for data sent to generative models?**

| Data Type | Classification | Safeguard |
|-----------|----------------|-----------|
| Issue descriptions | Internal | Only internal/sandbox repos processed |
| Source code | Internal | Only repos user has access to |
| CI/CD logs | Internal | Error messages only, no secrets |
| User data | None | No PII or customer data in workflow |

**Compliance:**

- Using approved Claude API endpoints
- AWS Bedrock option provides data residency in AWS
- No customer data or PII processed

### 4.6 Token Usage and Cost Estimates

**How are you estimating token consumption and associated costs?**

| Agent | Model | Est. Tokens/Workflow | Est. Cost/Workflow |
|-------|-------|---------------------|-------------------|
| Planning | Claude Opus | 10K-50K | ~$0.50 |
| Coding | Claude Sonnet | 50K-400K | ~$4.00 |
| Review | Claude Sonnet | 5K-20K | ~$0.15 |
| **Total** | | 65K-470K | **$5-10** |

**Cost monitoring:**

- Experimental phase - monitoring via Anthropic/AWS dashboards
- No automated cost alerts (POC scale)
- Conservative agent timeouts limit runaway costs

**At scale (future):**

- 1,000 issues/week = $5,000-10,000/week in LLM costs
- ROI measured by developer time saved vs infrastructure cost

---

## Summary

| Section | Status | Notes |
|---------|--------|-------|
| Section 2: Core AI Architecture | Complete | Multi-agent system with human escalation |
| Section 3: In-House Model Dev | N/A | Using pre-trained Claude models |
| Section 4: Generative AI | Complete | Code generation with validation layers |
| Section 5: MLOps/Production | N/A | Experimental/POC - not production |

> [!info] Production Deployment
> If this project moves to production, Section 5 (MLOps & Production Review) will need to be completed covering deployment procedures, monitoring, SLAs, and deprecation plans.

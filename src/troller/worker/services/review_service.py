"""Review service for evaluating code quality and plan adherence.

This service orchestrates the review workflow:
1. Clone repository
2. Use Claude structured query to evaluate implementation
3. Return feedback for coding agent
4. Clean up cloned repository
"""

import time
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from troller.domain.models.commit import Commit, InternalReviewFeedback
from troller.domain.models.issue import Issue
from troller.domain.models.plan import Plan
from troller.worker.activities.activity_outputs import LLMMetadataOutput
from troller.worker.adapters.claude_client import ClaudeClient, StructuredQueryResult
from troller.worker.adapters.repo_cloner import RepoCloner


class ReviewResponse(BaseModel):
    """Structured response from Claude review agent.

    Attributes:
        approved: Whether the implementation passes review.
        comments: Review comments (internal only).
        suggested_changes: Specific changes to make if rejected.
    """

    approved: bool
    comments: list[str]
    suggested_changes: list[str]


class ReviewService:
    """Service for reviewing code implementation against plan.

    This service uses ClaudeClient to:
    1. Clone the target repository
    2. Use structured query to evaluate code against plan
    3. Return review feedback
    4. Clean up cloned repository

    Coordinates repository management and review workflow.
    """

    def __init__(
        self,
        claude_client: ClaudeClient,
        repo_cloner: RepoCloner,
        model: str | None = None,
    ) -> None:
        """Initialize review service.

        Args:
            claude_client: Claude API client for queries.
            repo_cloner: Repository cloner adapter for git operations.
            model: Model name to use for structured queries.
        """
        self._client = claude_client
        self._repo_cloner = repo_cloner
        self._model = model

    async def review_changes(
        self,
        commits: list[Commit],
        plan: Plan,
        issue: Issue,
        repo_owner: str,
        repo_name: str,
        branch_name: str,
    ) -> tuple[InternalReviewFeedback, LLMMetadataOutput]:
        """Review code implementation against plan.

        This method atomically:
        1. Clones the target repository
        2. Uses structured query to evaluate code
        3. Returns review feedback
        4. Cleans up the cloned repository

        Args:
            commits: List of commits from implementation.
            plan: Implementation plan to verify against.
            issue: GitHub issue being addressed.
            repo_owner: GitHub repository owner.
            repo_name: GitHub repository name.
            branch_name: Branch containing the implementation.

        Returns:
            Tuple of (InternalReviewFeedback domain object, LLM execution metadata).

        Raises:
            RuntimeError: If repository cloning or review fails.
        """
        temp_dir: Path | None = None
        start_time = time.monotonic()

        try:
            # Step 1: Clone the feature branch
            temp_dir, repo_path, commit_sha = await self._repo_cloner.clone_to_temp(
                repo_owner, repo_name, branch_name
            )

            # Step 2: Execute review using structured query
            feedback, query_result = await self._review(repo_path, commits, plan, issue)

            # Calculate duration
            duration_ms = int((time.monotonic() - start_time) * 1000)

            # Create LLM metadata from structured query result
            llm_metadata = LLMMetadataOutput(
                total_cost_usd=None,  # Messages API doesn't provide cost
                input_tokens=query_result.input_tokens,
                output_tokens=query_result.output_tokens,
                duration_ms=duration_ms,
                duration_api_ms=duration_ms,
                num_turns=1,
                model=query_result.model,
                tools_used=[],
                execution_flow="Structured review query",
            )

            return feedback, llm_metadata

        finally:
            # Step 3: Always cleanup, even if review fails
            if temp_dir and temp_dir.exists():
                self._repo_cloner.cleanup(temp_dir)

    async def _review(
        self,
        repo_path: Path,
        commits: list[Commit],
        plan: Plan,
        issue: Issue,
    ) -> tuple[InternalReviewFeedback, StructuredQueryResult[ReviewResponse]]:
        """Execute review using Claude structured query.

        Args:
            repo_path: Path to the cloned repository.
            commits: List of commits from implementation.
            plan: Implementation plan to verify against.
            issue: GitHub issue being addressed.

        Returns:
            Tuple of (InternalReviewFeedback domain object, StructuredQueryResult).
        """
        # Build prompt for review
        prompt = self._build_review_prompt(commits, plan, issue)

        # Execute structured query for consistent response
        query_result = await self._client.structured_query(
            prompt=prompt,
            schema=ReviewResponse,
            model=self._model,
        )

        # Convert to domain model
        feedback = InternalReviewFeedback(
            approved=query_result.result.approved,
            comments=query_result.result.comments,
            suggested_changes=query_result.result.suggested_changes,
            timestamp=datetime.now(UTC),
        )

        return feedback, query_result

    def _build_review_prompt(
        self,
        commits: list[Commit],
        plan: Plan,
        issue: Issue,
    ) -> str:
        """Build prompt for Claude to review the implementation.

        Args:
            commits: List of commits from implementation.
            plan: Implementation plan to verify against.
            issue: GitHub issue being addressed.

        Returns:
            Formatted prompt string for Claude.
        """
        # Build steps description
        steps_text = "\n".join(
            [f"{i + 1}. {step.description}" for i, step in enumerate(plan.steps)]
        )

        # Build commits description
        commits_text = "\n".join(
            [
                f"- Commit {commit.sha[:8]}: {commit.message.split(chr(10))[0]}"
                for commit in commits
            ]
        )

        # Build technical context
        technical_context = ""
        if plan.technical_approach:
            technical_context += f"\n\nTechnical Approach:\n{plan.technical_approach}"
        if plan.testing_strategy:
            technical_context += f"\n\nTesting Strategy:\n{plan.testing_strategy}"

        return f"""Review the implementation for GitHub issue #{issue.number}: {issue.title}

Issue Description:
{issue.description}

Implementation Plan:
{plan.summary}

Planned Steps:
{steps_text}
{technical_context}

Commits Made:
{commits_text}

Please evaluate the implementation against these criteria:

1. **Code Quality**: Does the code follow best practices, proper structure, and clean code principles?
2. **Plan Adherence**: Does the implementation match the planned steps and technical approach?
3. **Completeness**: Are all plan steps addressed in the implementation?
4. **Testing**: Are there appropriate tests following the testing strategy?

Respond with:
- approved: true if the implementation is acceptable, false if changes are needed
- comments: List of review observations (for internal agent feedback only)
- suggested_changes: If not approved, specific changes the implementation agent should make

Note: This is internal agent-to-agent feedback, NOT a public GitHub PR review."""

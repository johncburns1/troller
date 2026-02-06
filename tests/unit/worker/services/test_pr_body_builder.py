"""Tests for PR body builder service."""

from datetime import datetime, timezone

import pytest

from troller.domain.models.issue import Issue
from troller.worker.activities.activity_outputs import (
    CommitOutput,
    PlanOutput,
    PlanStepOutput,
)
from troller.worker.services.pr_body_builder import PRBodyBuilder


class TestPRBodyBuilder:
    """Tests for PRBodyBuilder service."""

    @pytest.fixture
    def builder(self) -> PRBodyBuilder:
        """Create PRBodyBuilder instance."""
        return PRBodyBuilder()

    @pytest.fixture
    def sample_issue(self) -> Issue:
        """Create sample issue for testing."""
        return Issue(
            number=42,
            title="Add user authentication",
            description="Implement OAuth2 authentication flow",
            labels=["enhancement", "security"],
            url="https://github.com/owner/repo/issues/42",
        )

    @pytest.fixture
    def sample_plan(self) -> PlanOutput:
        """Create sample plan for testing."""
        return PlanOutput(
            summary="Implement OAuth2 authentication with Google provider",
            steps=[
                PlanStepOutput(
                    id="step-1",
                    description="Create auth configuration module",
                    related_files=["src/auth/config.py"],
                ),
                PlanStepOutput(
                    id="step-2",
                    description="Implement OAuth2 flow handler",
                    related_files=["src/auth/oauth.py", "src/auth/handlers.py"],
                ),
                PlanStepOutput(
                    id="step-3",
                    description="Add authentication middleware",
                    related_files=["src/middleware/auth.py"],
                ),
            ],
            created_at=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            technical_approach="Use OAuth2 with PKCE flow for enhanced security. "
            "Store tokens in HTTP-only cookies.",
            testing_strategy="Unit tests for auth logic, integration tests for OAuth flow.",
        )

    @pytest.fixture
    def sample_commits(self) -> list[CommitOutput]:
        """Create sample commits for testing."""
        return [
            CommitOutput(
                sha="abc1234",
                message="Add auth configuration module",
                timestamp=datetime(2026, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
            ),
            CommitOutput(
                sha="def5678",
                message="Implement OAuth2 flow handler",
                timestamp=datetime(2026, 1, 15, 11, 30, 0, tzinfo=timezone.utc),
            ),
            CommitOutput(
                sha="ghi9012",
                message="Add authentication middleware",
                timestamp=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            ),
        ]

    def test_build_body_includes_issue_reference(
        self,
        builder: PRBodyBuilder,
        sample_issue: Issue,
        sample_plan: PlanOutput,
        sample_commits: list[CommitOutput],
    ) -> None:
        """PR body should reference the issue number."""
        body = builder.build(sample_issue, sample_plan, sample_commits)

        assert "Resolves #42" in body

    def test_build_body_includes_summary(
        self,
        builder: PRBodyBuilder,
        sample_issue: Issue,
        sample_plan: PlanOutput,
        sample_commits: list[CommitOutput],
    ) -> None:
        """PR body should include plan summary."""
        body = builder.build(sample_issue, sample_plan, sample_commits)

        assert "## Summary" in body
        assert "Implement OAuth2 authentication with Google provider" in body

    def test_build_body_includes_technical_approach(
        self,
        builder: PRBodyBuilder,
        sample_issue: Issue,
        sample_plan: PlanOutput,
        sample_commits: list[CommitOutput],
    ) -> None:
        """PR body should include technical approach."""
        body = builder.build(sample_issue, sample_plan, sample_commits)

        assert "## Technical Approach" in body
        assert "OAuth2 with PKCE flow" in body

    def test_build_body_includes_implementation_steps(
        self,
        builder: PRBodyBuilder,
        sample_issue: Issue,
        sample_plan: PlanOutput,
        sample_commits: list[CommitOutput],
    ) -> None:
        """PR body should include implementation steps."""
        body = builder.build(sample_issue, sample_plan, sample_commits)

        assert "## Implementation Steps" in body
        assert "Create auth configuration module" in body
        assert "Implement OAuth2 flow handler" in body
        assert "Add authentication middleware" in body

    def test_build_body_includes_testing_strategy(
        self,
        builder: PRBodyBuilder,
        sample_issue: Issue,
        sample_plan: PlanOutput,
        sample_commits: list[CommitOutput],
    ) -> None:
        """PR body should include testing strategy."""
        body = builder.build(sample_issue, sample_plan, sample_commits)

        assert "## Testing Strategy" in body
        assert "Unit tests for auth logic" in body

    def test_build_body_includes_commits(
        self,
        builder: PRBodyBuilder,
        sample_issue: Issue,
        sample_plan: PlanOutput,
        sample_commits: list[CommitOutput],
    ) -> None:
        """PR body should include commit list with SHA and message."""
        body = builder.build(sample_issue, sample_plan, sample_commits)

        assert "## Commits" in body
        assert "abc1234" in body
        assert "Add auth configuration module" in body
        assert "def5678" in body
        assert "ghi9012" in body

    def test_build_body_includes_footer(
        self,
        builder: PRBodyBuilder,
        sample_issue: Issue,
        sample_plan: PlanOutput,
        sample_commits: list[CommitOutput],
    ) -> None:
        """PR body should include Troller footer."""
        body = builder.build(sample_issue, sample_plan, sample_commits)

        assert "🤖 Generated by Troller" in body

    def test_build_body_handles_missing_technical_approach(
        self,
        builder: PRBodyBuilder,
        sample_issue: Issue,
        sample_commits: list[CommitOutput],
    ) -> None:
        """PR body should handle plan without technical approach."""
        plan = PlanOutput(
            summary="Simple fix",
            steps=[
                PlanStepOutput(id="step-1", description="Fix the bug"),
            ],
            created_at=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            technical_approach=None,
            testing_strategy="Manual testing",
        )

        body = builder.build(sample_issue, plan, sample_commits)

        assert "## Technical Approach" not in body
        assert "## Summary" in body

    def test_build_body_handles_missing_testing_strategy(
        self,
        builder: PRBodyBuilder,
        sample_issue: Issue,
        sample_commits: list[CommitOutput],
    ) -> None:
        """PR body should handle plan without testing strategy."""
        plan = PlanOutput(
            summary="Quick fix",
            steps=[
                PlanStepOutput(id="step-1", description="Fix the bug"),
            ],
            created_at=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            technical_approach="Simple approach",
            testing_strategy=None,
        )

        body = builder.build(sample_issue, plan, sample_commits)

        assert "## Testing Strategy" not in body
        assert "## Technical Approach" in body

    def test_build_body_handles_empty_commits(
        self,
        builder: PRBodyBuilder,
        sample_issue: Issue,
        sample_plan: PlanOutput,
    ) -> None:
        """PR body should handle empty commits list gracefully."""
        body = builder.build(sample_issue, sample_plan, [])

        assert "## Commits" not in body
        assert "## Summary" in body

    def test_build_body_handles_many_commits(
        self,
        builder: PRBodyBuilder,
        sample_issue: Issue,
        sample_plan: PlanOutput,
    ) -> None:
        """PR body should handle large number of commits."""
        many_commits = [
            CommitOutput(
                sha=f"sha{i:04d}",
                message=f"Commit message {i}",
                timestamp=datetime(
                    2026, 1, 15 + (i // 24), i % 24, 0, 0, tzinfo=timezone.utc
                ),
            )
            for i in range(20)
        ]

        body = builder.build(sample_issue, sample_plan, many_commits)

        # Should include all commits
        assert "sha0000" in body
        assert "sha0019" in body

    def test_build_body_formats_steps_as_numbered_list(
        self,
        builder: PRBodyBuilder,
        sample_issue: Issue,
        sample_plan: PlanOutput,
        sample_commits: list[CommitOutput],
    ) -> None:
        """Implementation steps should be formatted as numbered list."""
        body = builder.build(sample_issue, sample_plan, sample_commits)

        assert "1. Create auth configuration module" in body
        assert "2. Implement OAuth2 flow handler" in body
        assert "3. Add authentication middleware" in body

    def test_build_body_formats_commits_as_list(
        self,
        builder: PRBodyBuilder,
        sample_issue: Issue,
        sample_plan: PlanOutput,
        sample_commits: list[CommitOutput],
    ) -> None:
        """Commits should be formatted with SHA prefix."""
        body = builder.build(sample_issue, sample_plan, sample_commits)

        # Check commit format: `sha` - message
        assert "`abc1234`" in body
        assert "`def5678`" in body
        assert "`ghi9012`" in body

"""Unit tests for Review service."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage

from troller.domain.models.commit import Commit, InternalReviewFeedback
from troller.domain.models.issue import Issue
from troller.domain.models.plan import Plan, PlanStep
from troller.worker.adapters.claude_client import ClaudeClient
from troller.worker.adapters.repo_cloner import RepoCloner
from troller.worker.services.review_service import ReviewService


def make_mock_result_message(
    approved: bool,
    comments: list[str] | None = None,
    suggested_changes: list[str] | None = None,
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> MagicMock:
    """Create a mock ResultMessage for tests."""
    mock_result = MagicMock(spec=ResultMessage)
    mock_result.structured_output = {
        "approved": approved,
        "comments": comments or [],
        "suggested_changes": suggested_changes or [],
    }
    mock_result.usage = {"input_tokens": input_tokens, "output_tokens": output_tokens}
    mock_result.subtype = "success"
    return mock_result


def make_mock_query(
    approved: bool,
    comments: list[str] | None = None,
    suggested_changes: list[str] | None = None,
    input_tokens: int = 100,
    output_tokens: int = 50,
):
    """Create a mock query async iterator."""
    result_message = make_mock_result_message(
        approved, comments, suggested_changes, input_tokens, output_tokens
    )

    async def mock_query_response(prompt: str, options: ClaudeAgentOptions):
        yield result_message

    return mock_query_response


class TestReviewService:
    """Test suite for ReviewService."""

    @pytest.mark.asyncio
    async def test_review_changes_clones_feature_branch(self) -> None:
        """review_changes clones the feature branch for review."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client - returns approval
        mock_client = MagicMock(spec=ClaudeClient)
        mock_client.query = make_mock_query(approved=True)

        service = ReviewService(mock_client, mock_cloner)

        commits = [
            Commit(sha="abc123", message="Test commit", timestamp=datetime.now())
        ]
        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=False)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        await service.review_changes(
            commits=commits,
            plan=plan,
            issue=issue,
            repo_owner="testowner",
            repo_name="testrepo",
            branch_name="feature/test-branch",
        )

        # Verify clone_to_temp was called with the FEATURE branch name
        mock_cloner.clone_to_temp.assert_called_once_with(
            "testowner", "testrepo", "feature/test-branch"
        )

    @pytest.mark.asyncio
    async def test_review_changes_cleans_up_repository(self) -> None:
        """review_changes removes cloned repository after completion."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        temp_dir = MagicMock(spec=Path)
        temp_dir.exists.return_value = True
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(temp_dir, Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client - returns approval
        mock_client = MagicMock(spec=ClaudeClient)
        mock_client.query = make_mock_query(approved=True)

        service = ReviewService(mock_client, mock_cloner)

        commits = [
            Commit(sha="abc123", message="Test commit", timestamp=datetime.now())
        ]
        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=False)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        await service.review_changes(
            commits=commits,
            plan=plan,
            issue=issue,
            repo_owner="owner",
            repo_name="repo",
            branch_name="test-branch",
        )

        # Verify cleanup was called
        mock_cloner.cleanup.assert_called_once_with(temp_dir)

    @pytest.mark.asyncio
    async def test_review_changes_cleans_up_on_failure(self) -> None:
        """review_changes removes cloned repository even if review fails."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        temp_dir = MagicMock(spec=Path)
        temp_dir.exists.return_value = True
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(temp_dir, Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client with query that raises error
        mock_client = MagicMock(spec=ClaudeClient)

        async def failing_query(prompt: str, options: ClaudeAgentOptions):
            raise RuntimeError("Review failed")
            yield  # noqa: B901 - unreachable but needed for async generator type

        mock_client.query = failing_query

        service = ReviewService(mock_client, mock_cloner)

        commits = [
            Commit(sha="abc123", message="Test commit", timestamp=datetime.now())
        ]
        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=False)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        with pytest.raises(RuntimeError, match="Review failed"):
            await service.review_changes(
                commits=commits,
                plan=plan,
                issue=issue,
                repo_owner="owner",
                repo_name="repo",
                branch_name="test-branch",
            )

        # Verify cleanup still happened
        mock_cloner.cleanup.assert_called_once_with(temp_dir)

    @pytest.mark.asyncio
    async def test_review_changes_returns_approved_feedback(self) -> None:
        """review_changes returns InternalReviewFeedback when approved."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client - returns approval with comments
        mock_client = MagicMock(spec=ClaudeClient)
        mock_client.query = make_mock_query(
            approved=True,
            comments=["Code looks good", "Well tested"],
        )

        service = ReviewService(mock_client, mock_cloner)

        commits = [
            Commit(sha="abc123", message="Test commit", timestamp=datetime.now())
        ]
        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=True)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        feedback, llm_metadata = await service.review_changes(
            commits=commits,
            plan=plan,
            issue=issue,
            repo_owner="owner",
            repo_name="repo",
            branch_name="test-branch",
        )

        # Verify feedback structure
        assert isinstance(feedback, InternalReviewFeedback)
        assert feedback.approved is True
        assert feedback.comments == ["Code looks good", "Well tested"]
        assert feedback.suggested_changes == []

    @pytest.mark.asyncio
    async def test_review_changes_returns_rejected_feedback_with_changes(self) -> None:
        """review_changes returns InternalReviewFeedback with suggested changes when rejected."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client - returns rejection with changes
        mock_client = MagicMock(spec=ClaudeClient)
        mock_client.query = make_mock_query(
            approved=False,
            comments=["Missing test coverage", "Code style issues"],
            suggested_changes=[
                "Add unit tests for edge cases",
                "Fix formatting in service.py",
            ],
        )

        service = ReviewService(mock_client, mock_cloner)

        commits = [
            Commit(sha="abc123", message="Test commit", timestamp=datetime.now())
        ]
        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=False)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        feedback, llm_metadata = await service.review_changes(
            commits=commits,
            plan=plan,
            issue=issue,
            repo_owner="owner",
            repo_name="repo",
            branch_name="test-branch",
        )

        # Verify feedback structure
        assert isinstance(feedback, InternalReviewFeedback)
        assert feedback.approved is False
        assert "Missing test coverage" in feedback.comments
        assert "Add unit tests for edge cases" in feedback.suggested_changes

    @pytest.mark.asyncio
    async def test_review_changes_passes_cwd_to_query(self) -> None:
        """review_changes passes repo_path as cwd to Claude query."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture options
        mock_client = MagicMock(spec=ClaudeClient)
        captured_options: list[ClaudeAgentOptions] = []

        async def capture_options(prompt: str, options: ClaudeAgentOptions):
            captured_options.append(options)
            mock_result = make_mock_result_message(approved=True)
            yield mock_result

        mock_client.query = capture_options

        service = ReviewService(mock_client, mock_cloner)

        commits = [
            Commit(sha="abc123", message="Test commit", timestamp=datetime.now())
        ]
        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=True)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        await service.review_changes(
            commits=commits,
            plan=plan,
            issue=issue,
            repo_owner="owner",
            repo_name="repo",
            branch_name="test-branch",
        )

        # Verify cwd was set to repo_path
        assert len(captured_options) > 0
        options = captured_options[0]
        assert options.cwd == "/tmp/test/repo"

    @pytest.mark.asyncio
    async def test_review_changes_uses_read_only_tools(self) -> None:
        """review_changes configures allowed_tools for read-only code inspection."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture options
        mock_client = MagicMock(spec=ClaudeClient)
        captured_options: list[ClaudeAgentOptions] = []

        async def capture_options(prompt: str, options: ClaudeAgentOptions):
            captured_options.append(options)
            mock_result = make_mock_result_message(approved=True)
            yield mock_result

        mock_client.query = capture_options

        service = ReviewService(mock_client, mock_cloner)

        commits = [
            Commit(sha="abc123", message="Test commit", timestamp=datetime.now())
        ]
        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=True)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        await service.review_changes(
            commits=commits,
            plan=plan,
            issue=issue,
            repo_owner="owner",
            repo_name="repo",
            branch_name="test-branch",
        )

        # Verify allowed_tools includes read-only tools
        assert len(captured_options) > 0
        options = captured_options[0]
        assert "Read" in options.allowed_tools
        assert "Grep" in options.allowed_tools
        assert "Glob" in options.allowed_tools
        # Should NOT include write tools
        assert "Write" not in options.allowed_tools
        assert "Edit" not in options.allowed_tools

    @pytest.mark.asyncio
    async def test_review_changes_uses_structured_output(self) -> None:
        """review_changes configures output_format for structured JSON output."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture options
        mock_client = MagicMock(spec=ClaudeClient)
        captured_options: list[ClaudeAgentOptions] = []

        async def capture_options(prompt: str, options: ClaudeAgentOptions):
            captured_options.append(options)
            mock_result = make_mock_result_message(approved=True)
            yield mock_result

        mock_client.query = capture_options

        service = ReviewService(mock_client, mock_cloner)

        commits = [
            Commit(sha="abc123", message="Test commit", timestamp=datetime.now())
        ]
        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=True)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        await service.review_changes(
            commits=commits,
            plan=plan,
            issue=issue,
            repo_owner="owner",
            repo_name="repo",
            branch_name="test-branch",
        )

        # Verify output_format is configured
        assert len(captured_options) > 0
        options = captured_options[0]
        assert options.output_format is not None
        assert options.output_format["type"] == "json_schema"
        assert "schema" in options.output_format

    @pytest.mark.asyncio
    async def test_review_changes_includes_plan_and_issue_in_prompt(self) -> None:
        """review_changes includes plan summary and issue details in prompt."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture prompt
        mock_client = MagicMock(spec=ClaudeClient)
        captured_prompts: list[str] = []

        async def capture_prompt(prompt: str, options: ClaudeAgentOptions):
            captured_prompts.append(prompt)
            mock_result = make_mock_result_message(approved=True)
            yield mock_result

        mock_client.query = capture_prompt

        service = ReviewService(mock_client, mock_cloner)

        commits = [
            Commit(sha="abc123", message="Test commit", timestamp=datetime.now())
        ]
        plan = Plan(
            summary="Add user authentication with JWT",
            steps=[
                PlanStep(
                    id="step-1", description="Implement JWT middleware", completed=True
                )
            ],
            created_at=datetime.now(),
            technical_approach="Use hexagonal architecture",
            testing_strategy="Unit tests for domain logic",
        )
        issue = Issue(
            number=55,
            title="Auth System",
            description="Implement authentication system",
        )

        await service.review_changes(
            commits=commits,
            plan=plan,
            issue=issue,
            repo_owner="owner",
            repo_name="repo",
            branch_name="auth-branch",
        )

        # Verify prompt includes details
        assert len(captured_prompts) > 0
        prompt = captured_prompts[0]
        assert "55" in prompt or "Auth System" in prompt
        assert "authentication" in prompt.lower()
        assert "JWT" in prompt

    @pytest.mark.asyncio
    async def test_review_changes_includes_commit_diffs_in_prompt(self) -> None:
        """review_changes includes commit information in the review prompt."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture prompt
        mock_client = MagicMock(spec=ClaudeClient)
        captured_prompts: list[str] = []

        async def capture_prompt(prompt: str, options: ClaudeAgentOptions):
            captured_prompts.append(prompt)
            mock_result = make_mock_result_message(approved=True)
            yield mock_result

        mock_client.query = capture_prompt

        service = ReviewService(mock_client, mock_cloner)

        commits = [
            Commit(
                sha="abc123def456",
                message="Implement feature X\n\nDetailed description here",
                timestamp=datetime.now(),
            ),
            Commit(
                sha="def456ghi789",
                message="Add tests for feature X",
                timestamp=datetime.now(),
            ),
        ]
        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=True)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        await service.review_changes(
            commits=commits,
            plan=plan,
            issue=issue,
            repo_owner="owner",
            repo_name="repo",
            branch_name="test-branch",
        )

        # Verify prompt includes commit info
        assert len(captured_prompts) > 0
        prompt = captured_prompts[0]
        assert "abc123def456" in prompt or "Implement feature X" in prompt

    @pytest.mark.asyncio
    async def test_review_changes_returns_llm_metadata(self) -> None:
        """review_changes returns LLM metadata for cost tracking."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client
        mock_client = MagicMock(spec=ClaudeClient)
        mock_client.query = make_mock_query(
            approved=True,
            input_tokens=200,
            output_tokens=75,
        )

        service = ReviewService(mock_client, mock_cloner)

        commits = [
            Commit(sha="abc123", message="Test commit", timestamp=datetime.now())
        ]
        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=True)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        feedback, llm_metadata = await service.review_changes(
            commits=commits,
            plan=plan,
            issue=issue,
            repo_owner="owner",
            repo_name="repo",
            branch_name="test-branch",
        )

        # Verify metadata structure
        assert llm_metadata is not None
        assert llm_metadata.duration_ms >= 0
        assert llm_metadata.num_turns == 1
        assert llm_metadata.input_tokens == 200
        assert llm_metadata.output_tokens == 75

    @pytest.mark.asyncio
    async def test_review_raises_error_when_no_result_message(self) -> None:
        """review_changes raises RuntimeError when no ResultMessage received."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client that yields no ResultMessage
        mock_client = MagicMock(spec=ClaudeClient)

        async def empty_query(prompt: str, options: ClaudeAgentOptions):
            yield MagicMock()  # Not a ResultMessage

        mock_client.query = empty_query

        service = ReviewService(mock_client, mock_cloner)

        commits = [
            Commit(sha="abc123", message="Test commit", timestamp=datetime.now())
        ]
        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=True)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        with pytest.raises(RuntimeError, match="No result message received"):
            await service.review_changes(
                commits=commits,
                plan=plan,
                issue=issue,
                repo_owner="owner",
                repo_name="repo",
                branch_name="test-branch",
            )

    @pytest.mark.asyncio
    async def test_review_raises_error_when_no_structured_output(self) -> None:
        """review_changes raises RuntimeError when structured_output is None."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client that returns ResultMessage without structured_output
        mock_client = MagicMock(spec=ClaudeClient)

        async def no_structured_query(prompt: str, options: ClaudeAgentOptions):
            mock_result = MagicMock(spec=ResultMessage)
            mock_result.structured_output = None
            mock_result.subtype = "error_max_turns"
            yield mock_result

        mock_client.query = no_structured_query

        service = ReviewService(mock_client, mock_cloner)

        commits = [
            Commit(sha="abc123", message="Test commit", timestamp=datetime.now())
        ]
        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=True)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        with pytest.raises(RuntimeError, match="No structured output.*error_max_turns"):
            await service.review_changes(
                commits=commits,
                plan=plan,
                issue=issue,
                repo_owner="owner",
                repo_name="repo",
                branch_name="test-branch",
            )

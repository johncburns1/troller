"""Unit tests for Implementation service."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from troller.domain.models.commit import Commit
from troller.domain.models.issue import Issue
from troller.domain.models.plan import Plan, PlanStep
from troller.worker.adapters.claude_client import ClaudeClient
from troller.worker.adapters.git_operations import GitOperations
from troller.worker.adapters.repo_cloner import RepoCloner
from troller.worker.services.implementation_service import ImplementationService


class MockResultMessage:
    """Mock result message with metadata."""

    def __init__(self):
        self.subtype = "result"


class TestImplementationService:
    """Test suite for ImplementationService."""

    @pytest.mark.asyncio
    async def test_implement_changes_clones_feature_branch(self) -> None:
        """implement_changes clones the feature branch (not target branch)."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MockResultMessage()

        mock_client.query = mock_query_response

        # Mock GitOperations
        mock_git = MagicMock(spec=GitOperations)
        mock_git.commit_changes = AsyncMock()
        mock_git.get_current_sha = AsyncMock(return_value="def456")
        mock_git.push_branch = AsyncMock()

        service = ImplementationService(mock_client, mock_cloner, mock_git)

        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=False)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        await service.implement_changes(
            plan=plan,
            issue=issue,
            repo_owner="testowner",
            repo_name="testrepo",
            branch_name="feature/test-branch",
        )

        # Verify clone_to_temp was called with the FEATURE branch name (not target_branch)
        # This ensures the implementation works on the pre-created feature branch
        mock_cloner.clone_to_temp.assert_called_once_with(
            "testowner", "testrepo", "feature/test-branch"
        )

    @pytest.mark.asyncio
    async def test_implement_changes_cleans_up_repository(self) -> None:
        """implement_changes removes cloned repository after completion."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        temp_dir = MagicMock(spec=Path)
        temp_dir.exists.return_value = True
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(temp_dir, Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MockResultMessage()

        mock_client.query = mock_query_response

        # Mock GitOperations
        mock_git = MagicMock(spec=GitOperations)
        mock_git.commit_changes = AsyncMock()
        mock_git.get_current_sha = AsyncMock(return_value="def456")
        mock_git.push_branch = AsyncMock()

        service = ImplementationService(mock_client, mock_cloner, mock_git)

        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=False)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        await service.implement_changes(
            plan=plan,
            issue=issue,
            repo_owner="owner",
            repo_name="repo",
            branch_name="test-branch",
        )

        # Verify cleanup was called
        mock_cloner.cleanup.assert_called_once_with(temp_dir)

    @pytest.mark.asyncio
    async def test_implement_changes_cleans_up_on_failure(self) -> None:
        """implement_changes removes cloned repository even if implementation fails."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        temp_dir = MagicMock(spec=Path)
        temp_dir.exists.return_value = True
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(temp_dir, Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client with failing query
        mock_client = MagicMock(spec=ClaudeClient)

        async def failing_query(*args, **kwargs):
            raise RuntimeError("Agent failed")
            yield  # Make it async generator (but never reached)

        mock_client.query = failing_query

        # Mock GitOperations
        mock_git = MagicMock(spec=GitOperations)

        service = ImplementationService(mock_client, mock_cloner, mock_git)

        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=False)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        with pytest.raises(RuntimeError, match="Agent failed"):
            await service.implement_changes(
                plan=plan,
                issue=issue,
                repo_owner="owner",
                repo_name="repo",
                branch_name="test-branch",
            )

        # Verify cleanup still happened
        mock_cloner.cleanup.assert_called_once_with(temp_dir)

    @pytest.mark.asyncio
    async def test_implement_changes_commits_and_pushes(self) -> None:
        """implement_changes commits changes and pushes to remote."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MockResultMessage()

        mock_client.query = mock_query_response

        # Mock GitOperations
        mock_git = MagicMock(spec=GitOperations)
        mock_git.commit_changes = AsyncMock()
        mock_git.get_current_sha = AsyncMock(return_value="def456")
        mock_git.push_branch = AsyncMock()

        service = ImplementationService(mock_client, mock_cloner, mock_git)

        plan = Plan(
            summary="Test plan",
            steps=[
                PlanStep(
                    id="step-1", description="Implement feature X", completed=False
                )
            ],
            created_at=datetime.now(),
        )
        issue = Issue(number=42, title="Test Issue", description="Test description")

        await service.implement_changes(
            plan=plan,
            issue=issue,
            repo_owner="owner",
            repo_name="repo",
            branch_name="feature-branch",
        )

        # Verify git operations were called
        mock_git.commit_changes.assert_called_once()
        mock_git.get_current_sha.assert_called_once_with(str(Path("/tmp/test/repo")))
        mock_git.push_branch.assert_called_once_with(
            repo_path=str(Path("/tmp/test/repo")),
            branch_name="feature-branch",
            force=False,
            set_upstream=True,
        )

    @pytest.mark.asyncio
    async def test_implement_changes_returns_commit_with_metadata(self) -> None:
        """implement_changes returns Commit domain model with SHA and metadata."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MockResultMessage()

        mock_client.query = mock_query_response

        # Mock GitOperations
        mock_git = MagicMock(spec=GitOperations)
        mock_git.commit_changes = AsyncMock()
        mock_git.get_current_sha = AsyncMock(return_value="commit-sha-123")
        mock_git.push_branch = AsyncMock()

        service = ImplementationService(mock_client, mock_cloner, mock_git)

        plan = Plan(
            summary="Implement authentication",
            steps=[
                PlanStep(id="step-1", description="Add JWT support", completed=False)
            ],
            created_at=datetime.now(),
        )
        issue = Issue(number=99, title="Auth Feature", description="Add authentication")

        commits, llm_metadata = await service.implement_changes(
            plan=plan,
            issue=issue,
            repo_owner="owner",
            repo_name="repo",
            branch_name="auth-feature",
        )

        # Verify commit structure
        assert len(commits) == 1
        assert isinstance(commits[0], Commit)
        assert commits[0].sha == "commit-sha-123"
        assert "issue #99" in commits[0].message.lower() or "99" in commits[0].message

    @pytest.mark.asyncio
    async def test_implement_changes_enables_codebase_tools(self) -> None:
        """implement_changes enables Read, Write, Edit, Bash, Glob, Grep tools."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture options
        mock_client = MagicMock(spec=ClaudeClient)
        captured_options = []

        async def capture_options(prompt, options):
            captured_options.append(options)
            yield MockResultMessage()

        mock_client.query = capture_options

        # Mock GitOperations
        mock_git = MagicMock(spec=GitOperations)
        mock_git.commit_changes = AsyncMock()
        mock_git.get_current_sha = AsyncMock(return_value="def456")
        mock_git.push_branch = AsyncMock()

        service = ImplementationService(mock_client, mock_cloner, mock_git)

        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=False)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        await service.implement_changes(
            plan=plan,
            issue=issue,
            repo_owner="owner",
            repo_name="repo",
            branch_name="test-branch",
        )

        # Verify tools are enabled
        assert len(captured_options) > 0
        options = captured_options[0]
        required_tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
        for tool in required_tools:
            assert tool in options.allowed_tools

    @pytest.mark.asyncio
    async def test_implement_changes_uses_bypass_permissions_mode(self) -> None:
        """implement_changes uses bypassPermissions for automated workflow."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture options
        mock_client = MagicMock(spec=ClaudeClient)
        captured_options = []

        async def capture_options(prompt, options):
            captured_options.append(options)
            yield MockResultMessage()

        mock_client.query = capture_options

        # Mock GitOperations
        mock_git = MagicMock(spec=GitOperations)
        mock_git.commit_changes = AsyncMock()
        mock_git.get_current_sha = AsyncMock(return_value="def456")
        mock_git.push_branch = AsyncMock()

        service = ImplementationService(mock_client, mock_cloner, mock_git)

        plan = Plan(
            summary="Test plan",
            steps=[PlanStep(id="step-1", description="Test", completed=False)],
            created_at=datetime.now(),
        )
        issue = Issue(number=1, title="Test", description="Test description")

        await service.implement_changes(
            plan=plan,
            issue=issue,
            repo_owner="owner",
            repo_name="repo",
            branch_name="test-branch",
        )

        # Verify permission mode
        assert len(captured_options) > 0
        options = captured_options[0]
        assert options.permission_mode == "bypassPermissions"

    @pytest.mark.asyncio
    async def test_implement_changes_includes_plan_and_issue_in_prompt(self) -> None:
        """implement_changes includes plan summary and issue details in prompt."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture prompt
        mock_client = MagicMock(spec=ClaudeClient)
        captured_prompts = []

        async def capture_prompt(prompt, options):
            captured_prompts.append(prompt)
            yield MockResultMessage()

        mock_client.query = capture_prompt

        # Mock GitOperations
        mock_git = MagicMock(spec=GitOperations)
        mock_git.commit_changes = AsyncMock()
        mock_git.get_current_sha = AsyncMock(return_value="def456")
        mock_git.push_branch = AsyncMock()

        service = ImplementationService(mock_client, mock_cloner, mock_git)

        plan = Plan(
            summary="Add user authentication with JWT",
            steps=[
                PlanStep(
                    id="step-1", description="Implement JWT middleware", completed=False
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

        await service.implement_changes(
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

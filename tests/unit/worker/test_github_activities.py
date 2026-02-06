"""Unit tests for GitHub activities."""

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from github.Issue import Issue as GithubIssue
from github.Label import Label as GithubLabel

from troller.domain.models.pull_request import PullRequest
from troller.worker.activities.github_activities import (
    CreateFeatureBranchInput,
    CreateFeatureBranchOutput,
    CreatePullRequestInput,
    CreatePullRequestOutput,
    FetchIssueInput,
    FetchIssueOutput,
    FetchPullRequestInput,
    FetchPullRequestOutput,
    create_feature_branch,
    create_pull_request,
    fetch_issue,
    fetch_pull_request,
)


class TestFetchIssue:
    """Test suite for fetch_issue activity."""

    @pytest.mark.asyncio
    async def test_fetch_issue_returns_issue_dataclass(self) -> None:
        """fetch_issue returns Issue dataclass with correct fields."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_client_class:
                # Setup mock
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                # Mock GitHub issue
                mock_label1 = MagicMock(spec=GithubLabel)
                mock_label1.name = "bug"
                mock_label2 = MagicMock(spec=GithubLabel)
                mock_label2.name = "priority:high"

                mock_github_issue = MagicMock(spec=GithubIssue)
                mock_github_issue.number = 42
                mock_github_issue.title = "Fix the bug"
                mock_github_issue.body = "This is a bug description"
                mock_github_issue.labels = [mock_label1, mock_label2]
                mock_github_issue.html_url = "https://github.com/owner/repo/issues/42"

                mock_client.get_issue.return_value = mock_github_issue

                # Test
                input_data = FetchIssueInput(
                    repo_owner="owner", repo_name="repo", issue_number=42
                )
                result = await fetch_issue(input_data)

                # Verify
                assert isinstance(result, FetchIssueOutput)
                assert result.number == 42
                assert result.title == "Fix the bug"
                assert result.description == "This is a bug description"
                assert result.labels == ["bug", "priority:high"]
                assert result.url == "https://github.com/owner/repo/issues/42"

    @pytest.mark.asyncio
    async def test_fetch_issue_calls_github_client_with_correct_args(self) -> None:
        """fetch_issue calls GitHubClient.get_issue with correct parameters."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_client_class:
                # Setup mock
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                mock_github_issue = MagicMock(spec=GithubIssue)
                mock_github_issue.number = 123
                mock_github_issue.title = "Test"
                mock_github_issue.body = "Description"
                mock_github_issue.labels = []
                mock_github_issue.html_url = "https://github.com/test/test/issues/123"

                mock_client.get_issue.return_value = mock_github_issue

                # Test
                input_data = FetchIssueInput(
                    repo_owner="test-owner", repo_name="test-repo", issue_number=123
                )
                await fetch_issue(input_data)

                # Verify
                mock_client.get_issue.assert_called_once_with(
                    owner="test-owner", repo="test-repo", issue_number=123
                )

    @pytest.mark.asyncio
    async def test_fetch_issue_handles_empty_body(self) -> None:
        """fetch_issue handles None body by converting to empty string."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_client_class:
                # Setup mock
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                mock_github_issue = MagicMock(spec=GithubIssue)
                mock_github_issue.number = 1
                mock_github_issue.title = "Issue with no body"
                mock_github_issue.body = None
                mock_github_issue.labels = []
                mock_github_issue.html_url = "https://github.com/owner/repo/issues/1"

                mock_client.get_issue.return_value = mock_github_issue

                # Test
                input_data = FetchIssueInput(
                    repo_owner="owner", repo_name="repo", issue_number=1
                )
                result = await fetch_issue(input_data)

                # Verify
                assert result.description == ""

    @pytest.mark.asyncio
    async def test_fetch_issue_extracts_label_names(self) -> None:
        """fetch_issue extracts label names from GitHub Label objects."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_client_class:
                # Setup mock
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                # Create multiple labels
                labels = []
                for name in ["enhancement", "documentation", "good-first-issue"]:
                    mock_label = MagicMock(spec=GithubLabel)
                    mock_label.name = name
                    labels.append(mock_label)

                mock_github_issue = MagicMock(spec=GithubIssue)
                mock_github_issue.number = 1
                mock_github_issue.title = "Test"
                mock_github_issue.body = "Body"
                mock_github_issue.labels = labels
                mock_github_issue.html_url = "https://github.com/owner/repo/issues/1"

                mock_client.get_issue.return_value = mock_github_issue

                # Test
                input_data = FetchIssueInput(
                    repo_owner="owner", repo_name="repo", issue_number=1
                )
                result = await fetch_issue(input_data)

                # Verify
                assert result.labels == [
                    "enhancement",
                    "documentation",
                    "good-first-issue",
                ]


class TestCreatePullRequest:
    """Test suite for create_pull_request activity."""

    @pytest.mark.asyncio
    async def test_create_pull_request_returns_pull_request_dataclass(self) -> None:
        """create_pull_request returns PullRequest dataclass with correct fields."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_client_class:
                # Setup mock
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                # Mock the pull request that will be returned
                mock_pr = PullRequest(
                    number=42,
                    url="https://github.com/owner/repo/pull/42",
                    head_branch="feature/test",
                    base_branch="main",
                    head_sha="abc123def456",
                    created_at=datetime(2024, 1, 1, 12, 0, 0),
                    state="open",
                )
                mock_client.create_pull_request.return_value = mock_pr

                # Test
                input_data = CreatePullRequestInput(
                    repo_owner="owner",
                    repo_name="repo",
                    title="Test PR",
                    body="Test description",
                    head_branch="feature/test",
                    base_branch="main",
                    draft=False,
                )
                result = await create_pull_request(input_data)

                # Verify
                assert isinstance(result, CreatePullRequestOutput)
                assert result.number == 42
                assert result.url == "https://github.com/owner/repo/pull/42"
                assert result.head_branch == "feature/test"
                assert result.base_branch == "main"
                assert result.head_sha == "abc123def456"

    @pytest.mark.asyncio
    async def test_create_pull_request_calls_github_client_with_correct_args(
        self,
    ) -> None:
        """create_pull_request calls GitHubClient.create_pull_request with correct parameters."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_client_class:
                # Setup mock
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                mock_pr = PullRequest(
                    number=1,
                    url="https://github.com/test/test/pull/1",
                    head_branch="feature/branch",
                    base_branch="develop",
                    head_sha="def456",
                    created_at=datetime(2024, 1, 1, 12, 0, 0),
                    state="open",
                )
                mock_client.create_pull_request.return_value = mock_pr

                # Test
                input_data = CreatePullRequestInput(
                    repo_owner="test-owner",
                    repo_name="test-repo",
                    title="Test PR Title",
                    body="Test PR Body",
                    head_branch="feature/branch",
                    base_branch="develop",
                    draft=True,
                )
                await create_pull_request(input_data)

                # Verify
                mock_client.create_pull_request.assert_called_once_with(
                    owner="test-owner",
                    repo="test-repo",
                    title="Test PR Title",
                    body="Test PR Body",
                    head_branch="feature/branch",
                    base_branch="develop",
                    draft=True,
                )

    @pytest.mark.asyncio
    async def test_create_pull_request_creates_draft_pr_when_draft_is_true(
        self,
    ) -> None:
        """create_pull_request creates draft PR when draft parameter is True."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_client_class:
                # Setup mock
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                mock_pr = PullRequest(
                    number=1,
                    url="https://github.com/owner/repo/pull/1",
                    head_branch="feature/wip",
                    base_branch="main",
                    head_sha="abc123",
                    created_at=datetime(2024, 1, 1, 12, 0, 0),
                    state="open",
                )
                mock_client.create_pull_request.return_value = mock_pr

                # Test
                input_data = CreatePullRequestInput(
                    repo_owner="owner",
                    repo_name="repo",
                    title="Draft PR",
                    body="Work in progress",
                    head_branch="feature/wip",
                    base_branch="main",
                    draft=True,
                )
                await create_pull_request(input_data)

                # Verify draft=True was passed
                call_kwargs = mock_client.create_pull_request.call_args.kwargs
                assert call_kwargs["draft"] is True


class TestCreateFeatureBranchInput:
    """Test suite for CreateFeatureBranchInput model."""

    def test_create_feature_branch_input_accepts_valid_data(self) -> None:
        """CreateFeatureBranchInput accepts valid repository and branch data."""
        input_data = CreateFeatureBranchInput(
            repo_owner="test-owner",
            repo_name="test-repo",
            branch_name="feature/test",
            base_branch="main",
        )

        assert input_data.repo_owner == "test-owner"
        assert input_data.repo_name == "test-repo"
        assert input_data.branch_name == "feature/test"
        assert input_data.base_branch == "main"

    def test_create_feature_branch_input_is_frozen(self) -> None:
        """CreateFeatureBranchInput is immutable (frozen)."""
        input_data = CreateFeatureBranchInput(
            repo_owner="owner",
            repo_name="repo",
            branch_name="branch",
            base_branch="main",
        )

        with pytest.raises(Exception):  # Pydantic raises ValidationError on frozen
            input_data.branch_name = "different-branch"  # type: ignore


class TestCreateFeatureBranchOutput:
    """Test suite for CreateFeatureBranchOutput model."""

    def test_create_feature_branch_output_accepts_valid_data(self) -> None:
        """CreateFeatureBranchOutput accepts valid branch and SHA data."""
        output_data = CreateFeatureBranchOutput(
            branch_name="feature/test", head_sha="abc123def456"
        )

        assert output_data.branch_name == "feature/test"
        assert output_data.head_sha == "abc123def456"

    def test_create_feature_branch_output_is_frozen(self) -> None:
        """CreateFeatureBranchOutput is immutable (frozen)."""
        output_data = CreateFeatureBranchOutput(
            branch_name="feature/test", head_sha="abc123"
        )

        with pytest.raises(Exception):
            output_data.head_sha = "different-sha"  # type: ignore


class TestCreateFeatureBranch:
    """Test suite for create_feature_branch activity."""

    @pytest.mark.asyncio
    async def test_create_feature_branch_clones_creates_and_pushes_branch(
        self,
    ) -> None:
        """create_feature_branch clones repo, creates branch, pushes, and cleans up."""
        with (
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
        ):
            # Setup mocks
            mock_cloner = MagicMock()
            mock_cloner_class.return_value = mock_cloner
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops

            # Mock clone_to_temp to return temp_dir, repo_path, commit_sha
            temp_dir = Path("/tmp/test-temp")
            repo_path = Path("/tmp/test-temp/test-repo")
            mock_cloner.clone_to_temp = AsyncMock(
                return_value=(temp_dir, repo_path, "base-sha-123")
            )

            # Mock git operations
            mock_git_ops.create_branch = AsyncMock()
            mock_git_ops.push_branch = AsyncMock()
            mock_git_ops.get_current_sha = AsyncMock(return_value="new-branch-sha-456")

            # Test
            input_data = CreateFeatureBranchInput(
                repo_owner="test-owner",
                repo_name="test-repo",
                branch_name="feature/test-branch",
                base_branch="main",
            )
            result = await create_feature_branch(input_data)

            # Verify clone was called
            mock_cloner.clone_to_temp.assert_called_once_with(
                "test-owner", "test-repo", "main"
            )

            # Verify branch creation
            mock_git_ops.create_branch.assert_called_once_with(
                str(repo_path), "feature/test-branch", "main"
            )

            # Verify push
            mock_git_ops.push_branch.assert_called_once_with(
                str(repo_path), "feature/test-branch", force=False, set_upstream=True
            )

            # Verify cleanup
            mock_cloner.cleanup.assert_called_once_with(temp_dir)

            # Verify result
            assert isinstance(result, CreateFeatureBranchOutput)
            assert result.branch_name == "feature/test-branch"
            assert result.head_sha == "new-branch-sha-456"

    @pytest.mark.asyncio
    async def test_create_feature_branch_cleans_up_on_error(self) -> None:
        """create_feature_branch cleans up temp directory even if git operations fail."""
        with (
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
        ):
            # Setup mocks
            mock_cloner = MagicMock()
            mock_cloner_class.return_value = mock_cloner
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops

            temp_dir = Path("/tmp/test-temp")
            repo_path = Path("/tmp/test-temp/test-repo")
            mock_cloner.clone_to_temp = AsyncMock(
                return_value=(temp_dir, repo_path, "base-sha")
            )

            # Make create_branch fail
            mock_git_ops.create_branch = AsyncMock(
                side_effect=RuntimeError("Git operation failed")
            )

            # Test
            input_data = CreateFeatureBranchInput(
                repo_owner="owner",
                repo_name="repo",
                branch_name="feature/branch",
                base_branch="main",
            )

            with pytest.raises(RuntimeError, match="Git operation failed"):
                await create_feature_branch(input_data)

            # Verify cleanup was called despite error
            mock_cloner.cleanup.assert_called_once_with(temp_dir)

    @pytest.mark.asyncio
    async def test_create_feature_branch_uses_provided_base_branch(self) -> None:
        """create_feature_branch uses the provided base_branch parameter."""
        with (
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
        ):
            # Setup mocks
            mock_cloner = MagicMock()
            mock_cloner_class.return_value = mock_cloner
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops

            temp_dir = Path("/tmp/test-temp")
            repo_path = Path("/tmp/test-temp/test-repo")
            mock_cloner.clone_to_temp = AsyncMock(
                return_value=(temp_dir, repo_path, "develop-sha")
            )
            mock_git_ops.create_branch = AsyncMock()
            mock_git_ops.push_branch = AsyncMock()
            mock_git_ops.get_current_sha = AsyncMock(return_value="branch-sha")

            # Test with develop as base branch
            input_data = CreateFeatureBranchInput(
                repo_owner="owner",
                repo_name="repo",
                branch_name="feature/new-feature",
                base_branch="develop",
            )
            await create_feature_branch(input_data)

            # Verify clone used develop
            mock_cloner.clone_to_temp.assert_called_once_with(
                "owner", "repo", "develop"
            )

            # Verify branch creation used develop
            mock_git_ops.create_branch.assert_called_once_with(
                str(repo_path), "feature/new-feature", "develop"
            )

    @pytest.mark.asyncio
    async def test_create_feature_branch_returns_correct_output_structure(self) -> None:
        """create_feature_branch returns CreateFeatureBranchOutput with branch name and SHA."""
        with (
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
        ):
            # Setup mocks
            mock_cloner = MagicMock()
            mock_cloner_class.return_value = mock_cloner
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops

            temp_dir = Path("/tmp/test-temp")
            repo_path = Path("/tmp/test-temp/repo")
            mock_cloner.clone_to_temp = AsyncMock(
                return_value=(temp_dir, repo_path, "base-commit")
            )
            mock_git_ops.create_branch = AsyncMock()
            mock_git_ops.push_branch = AsyncMock()
            mock_git_ops.get_current_sha = AsyncMock(return_value="abc123def456789")

            # Test
            input_data = CreateFeatureBranchInput(
                repo_owner="owner",
                repo_name="repo",
                branch_name="troller/issue-36",
                base_branch="main",
            )
            result = await create_feature_branch(input_data)

            # Verify output structure
            assert isinstance(result, CreateFeatureBranchOutput)
            assert result.branch_name == "troller/issue-36"
            assert result.head_sha == "abc123def456789"
            assert len(result.head_sha) > 0


class TestFetchPullRequestInput:
    """Test suite for FetchPullRequestInput model."""

    def test_fetch_pull_request_input_accepts_valid_data(self) -> None:
        """FetchPullRequestInput accepts valid repository and PR number."""
        input_data = FetchPullRequestInput(
            repo_owner="test-owner",
            repo_name="test-repo",
            pr_number=42,
        )

        assert input_data.repo_owner == "test-owner"
        assert input_data.repo_name == "test-repo"
        assert input_data.pr_number == 42

    def test_fetch_pull_request_input_is_frozen(self) -> None:
        """FetchPullRequestInput is immutable (frozen)."""
        input_data = FetchPullRequestInput(
            repo_owner="owner",
            repo_name="repo",
            pr_number=1,
        )

        with pytest.raises(Exception):  # Pydantic raises ValidationError on frozen
            input_data.pr_number = 2  # type: ignore


class TestFetchPullRequestOutput:
    """Test suite for FetchPullRequestOutput model."""

    def test_fetch_pull_request_output_accepts_valid_data(self) -> None:
        """FetchPullRequestOutput accepts valid PR data."""
        output_data = FetchPullRequestOutput(
            number=42,
            url="https://github.com/owner/repo/pull/42",
            state="open",
            merged_at=None,
            merged_by=None,
        )

        assert output_data.number == 42
        assert output_data.url == "https://github.com/owner/repo/pull/42"
        assert output_data.state == "open"
        assert output_data.merged_at is None
        assert output_data.merged_by is None

    def test_fetch_pull_request_output_accepts_merged_data(self) -> None:
        """FetchPullRequestOutput accepts merged PR data."""
        output_data = FetchPullRequestOutput(
            number=42,
            url="https://github.com/owner/repo/pull/42",
            state="merged",
            merged_at="2024-01-02T12:00:00",
            merged_by="reviewer",
        )

        assert output_data.state == "merged"
        assert output_data.merged_at == "2024-01-02T12:00:00"
        assert output_data.merged_by == "reviewer"

    def test_fetch_pull_request_output_is_frozen(self) -> None:
        """FetchPullRequestOutput is immutable (frozen)."""
        output_data = FetchPullRequestOutput(
            number=42,
            url="https://github.com/owner/repo/pull/42",
            state="open",
            merged_at=None,
            merged_by=None,
        )

        with pytest.raises(Exception):
            output_data.state = "merged"  # type: ignore


class TestFetchPullRequest:
    """Test suite for fetch_pull_request activity."""

    @pytest.mark.asyncio
    async def test_fetch_pull_request_returns_output_with_correct_fields(self) -> None:
        """fetch_pull_request returns FetchPullRequestOutput with correct fields."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_client_class:
                # Setup mock
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                # Mock the pull request that will be returned
                mock_pr = PullRequest(
                    number=42,
                    url="https://github.com/owner/repo/pull/42",
                    head_branch="feature/test",
                    base_branch="main",
                    head_sha="abc123def456",
                    created_at=datetime(2024, 1, 1, 12, 0, 0),
                    state="open",
                )
                mock_client.get_pull_request.return_value = mock_pr

                # Test
                input_data = FetchPullRequestInput(
                    repo_owner="owner",
                    repo_name="repo",
                    pr_number=42,
                )
                result = await fetch_pull_request(input_data)

                # Verify
                assert isinstance(result, FetchPullRequestOutput)
                assert result.number == 42
                assert result.url == "https://github.com/owner/repo/pull/42"
                assert result.state == "open"
                assert result.merged_at is None
                assert result.merged_by is None

    @pytest.mark.asyncio
    async def test_fetch_pull_request_calls_github_client_with_correct_args(
        self,
    ) -> None:
        """fetch_pull_request calls GitHubClient.get_pull_request with correct parameters."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_client_class:
                # Setup mock
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                mock_pr = PullRequest(
                    number=123,
                    url="https://github.com/test/test/pull/123",
                    head_branch="feature/branch",
                    base_branch="main",
                    head_sha="def456",
                    created_at=datetime(2024, 1, 1, 12, 0, 0),
                    state="open",
                )
                mock_client.get_pull_request.return_value = mock_pr

                # Test
                input_data = FetchPullRequestInput(
                    repo_owner="test-owner",
                    repo_name="test-repo",
                    pr_number=123,
                )
                await fetch_pull_request(input_data)

                # Verify
                mock_client.get_pull_request.assert_called_once_with(
                    owner="test-owner",
                    repo="test-repo",
                    pr_number=123,
                )

    @pytest.mark.asyncio
    async def test_fetch_pull_request_returns_merged_state(self) -> None:
        """fetch_pull_request returns merged state with merged_at and merged_by."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_client_class:
                # Setup mock
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                # Mock the client to return a PR with merged state and metadata
                merged_at = datetime(2024, 1, 2, 12, 0, 0)
                mock_pr = PullRequest(
                    number=42,
                    url="https://github.com/owner/repo/pull/42",
                    head_branch="feature/test",
                    base_branch="main",
                    head_sha="abc123",
                    created_at=datetime(2024, 1, 1, 12, 0, 0),
                    state="merged",
                    merged_at=merged_at,
                    merged_by="reviewer",
                )
                mock_client.get_pull_request.return_value = mock_pr

                # Test
                input_data = FetchPullRequestInput(
                    repo_owner="owner",
                    repo_name="repo",
                    pr_number=42,
                )
                result = await fetch_pull_request(input_data)

                # Verify merged state and metadata
                assert result.state == "merged"
                assert result.merged_at == merged_at.isoformat()
                assert result.merged_by == "reviewer"

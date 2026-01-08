"""Unit tests for GitHub activities."""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from github.Issue import Issue as GithubIssue
from github.Label import Label as GithubLabel

from troller.domain.models.pull_request import PullRequest
from troller.worker.activities.github_activities import (
    CreatePullRequestInput,
    CreatePullRequestOutput,
    FetchIssueInput,
    FetchIssueOutput,
    create_pull_request,
    fetch_issue,
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

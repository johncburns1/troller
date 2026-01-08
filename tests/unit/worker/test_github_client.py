"""Unit tests for GitHub API client adapter."""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from github import Auth
from github.Issue import Issue as GithubIssue

from troller.domain.models.pull_request import PullRequest
from troller.worker.adapters.github_client import GitHubClient


class TestGitHubClient:
    """Test suite for GitHubClient adapter."""

    def test_init_reads_token_from_env(self) -> None:
        """GitHubClient reads GITHUB_TOKEN from environment."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch("troller.worker.adapters.github_client.Github") as mock_github:
                _client = GitHubClient()

                # Verify Github was instantiated with token auth
                mock_github.assert_called_once()
                call_kwargs = mock_github.call_args.kwargs
                assert "auth" in call_kwargs
                auth = call_kwargs["auth"]
                assert isinstance(auth, Auth.Token)

    def test_init_raises_error_when_token_missing(self) -> None:
        """GitHubClient raises clear error when GITHUB_TOKEN is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="GITHUB_TOKEN environment variable is required"
            ):
                GitHubClient()

    def test_get_issue_fetches_issue_by_repo_and_number(self) -> None:
        """get_issue fetches issue by owner, repo, and number."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.adapters.github_client.Github"
            ) as mock_github_class:
                # Setup mock
                mock_github = MagicMock()
                mock_github_class.return_value = mock_github

                mock_repo = MagicMock()
                mock_github.get_repo.return_value = mock_repo

                mock_issue = MagicMock(spec=GithubIssue)
                mock_issue.number = 123
                mock_issue.title = "Test Issue"
                mock_issue.body = "Test body"
                mock_repo.get_issue.return_value = mock_issue

                # Test
                client = GitHubClient()
                issue = client.get_issue("owner", "repo", 123)

                # Verify
                mock_github.get_repo.assert_called_once_with("owner/repo")
                mock_repo.get_issue.assert_called_once_with(123)
                assert issue == mock_issue

    def test_get_issue_returns_github_issue_object(self) -> None:
        """get_issue returns PyGithub Issue object."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.adapters.github_client.Github"
            ) as mock_github_class:
                # Setup mock
                mock_github = MagicMock()
                mock_github_class.return_value = mock_github

                mock_repo = MagicMock()
                mock_github.get_repo.return_value = mock_repo

                mock_issue = MagicMock(spec=GithubIssue)
                mock_repo.get_issue.return_value = mock_issue

                # Test
                client = GitHubClient()
                issue = client.get_issue("owner", "repo", 1)

                # Verify type
                assert isinstance(
                    issue, MagicMock
                )  # In real usage, would be GithubIssue

    def test_create_pull_request_creates_pr_and_returns_domain_model(
        self,
    ) -> None:
        """create_pull_request creates PR on GitHub and returns domain PullRequest."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.adapters.github_client.Github"
            ) as mock_github_class:
                # Setup mocks
                mock_github = MagicMock()
                mock_github_class.return_value = mock_github

                mock_repo = MagicMock()
                mock_github.get_repo.return_value = mock_repo

                # Mock the created pull request
                mock_pr = MagicMock()
                mock_pr.number = 42
                mock_pr.html_url = "https://github.com/owner/repo/pull/42"
                mock_pr.head.sha = "abc123def456"
                mock_pr.created_at = datetime(2024, 1, 1, 12, 0, 0)
                mock_pr.state = "open"
                mock_repo.create_pull.return_value = mock_pr

                # Test
                client = GitHubClient()
                result = client.create_pull_request(
                    owner="owner",
                    repo="repo",
                    title="Test PR",
                    body="Test description",
                    head_branch="feature/test",
                    base_branch="main",
                    draft=False,
                )

                # Verify create_pull was called correctly
                mock_repo.create_pull.assert_called_once_with(
                    title="Test PR",
                    body="Test description",
                    head="feature/test",
                    base="main",
                    draft=False,
                )

                # Verify domain model returned
                assert isinstance(result, PullRequest)
                assert result.number == 42
                assert result.url == "https://github.com/owner/repo/pull/42"
                assert result.head_sha == "abc123def456"
                assert result.created_at == datetime(2024, 1, 1, 12, 0, 0)
                assert result.state == "open"

    def test_create_pull_request_creates_draft_pr_when_draft_is_true(
        self,
    ) -> None:
        """create_pull_request creates draft PR when draft parameter is True."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.adapters.github_client.Github"
            ) as mock_github_class:
                # Setup mocks
                mock_github = MagicMock()
                mock_github_class.return_value = mock_github

                mock_repo = MagicMock()
                mock_github.get_repo.return_value = mock_repo

                mock_pr = MagicMock()
                mock_pr.number = 1
                mock_pr.html_url = "https://github.com/owner/repo/pull/1"
                mock_pr.head.sha = "def456"
                mock_pr.created_at = datetime(2024, 1, 1, 12, 0, 0)
                mock_pr.state = "open"
                mock_repo.create_pull.return_value = mock_pr

                # Test
                client = GitHubClient()
                client.create_pull_request(
                    owner="owner",
                    repo="repo",
                    title="Draft PR",
                    body="Work in progress",
                    head_branch="feature/draft",
                    base_branch="main",
                    draft=True,
                )

                # Verify draft=True was passed
                call_kwargs = mock_repo.create_pull.call_args.kwargs
                assert call_kwargs["draft"] is True

    def test_create_pull_request_uses_correct_repo_path(self) -> None:
        """create_pull_request gets repository using owner/repo format."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch(
                "troller.worker.adapters.github_client.Github"
            ) as mock_github_class:
                # Setup mocks
                mock_github = MagicMock()
                mock_github_class.return_value = mock_github

                mock_repo = MagicMock()
                mock_github.get_repo.return_value = mock_repo

                mock_pr = MagicMock()
                mock_pr.number = 1
                mock_pr.html_url = "https://github.com/test-owner/test-repo/pull/1"
                mock_pr.head.sha = "abc123"
                mock_pr.created_at = datetime(2024, 1, 1, 12, 0, 0)
                mock_pr.state = "open"
                mock_repo.create_pull.return_value = mock_pr

                # Test
                client = GitHubClient()
                client.create_pull_request(
                    owner="test-owner",
                    repo="test-repo",
                    title="Test",
                    body="Body",
                    head_branch="feature/test",
                    base_branch="main",
                )

                # Verify correct repo path
                mock_github.get_repo.assert_called_once_with("test-owner/test-repo")

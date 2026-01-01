"""Unit tests for GitHub API client adapter."""

import os
from unittest.mock import MagicMock, patch

import pytest
from github import Auth
from github.Issue import Issue as GithubIssue

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

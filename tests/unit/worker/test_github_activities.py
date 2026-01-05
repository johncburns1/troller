"""Unit tests for GitHub activities."""

import os
from unittest.mock import MagicMock, patch

import pytest
from github.Issue import Issue as GithubIssue
from github.Label import Label as GithubLabel

from troller.worker.activities.github_activities import FetchIssueInput, fetch_issue
from troller.worker.workflows.data_structures import Issue


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
                assert isinstance(result, Issue)
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

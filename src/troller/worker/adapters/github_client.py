"""GitHub API client adapter.

Adapter for interacting with GitHub via PyGithub library.
"""

import os

from github import Auth, Github
from github.Issue import Issue as GithubIssue


class GitHubClient:
    """GitHub API client for fetching issues and repository information.

    This is an adapter that wraps PyGithub to provide GitHub integration.
    Authenticates using a GitHub personal access token from environment.
    """

    def __init__(self) -> None:
        """Initialize GitHub client with token authentication.

        Raises:
            ValueError: If GITHUB_TOKEN environment variable is not set.
        """
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable is required")

        auth = Auth.Token(token)
        self._client = Github(auth=auth)

    def get_issue(self, owner: str, repo: str, issue_number: int) -> GithubIssue:
        """Fetch a GitHub issue by repository and issue number.

        Args:
            owner: Repository owner (user or organization).
            repo: Repository name.
            issue_number: Issue number to fetch.

        Returns:
            PyGithub Issue object containing issue details.
        """
        repository = self._client.get_repo(f"{owner}/{repo}")
        return repository.get_issue(issue_number)

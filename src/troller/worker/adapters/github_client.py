"""GitHub API client adapter.

Adapter for interacting with GitHub via PyGithub library.
"""

import os

from github import Auth, Github
from github.Issue import Issue as GithubIssue

from troller.domain.models.pull_request import PullRequest


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

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
        draft: bool = False,
    ) -> PullRequest:
        """Create a pull request on GitHub.

        Args:
            owner: Repository owner (user or organization).
            repo: Repository name.
            title: Pull request title.
            body: Pull request description/body.
            head_branch: Branch containing the changes.
            base_branch: Branch to merge changes into (e.g., 'main').
            draft: Whether to create as draft PR (default: False).

        Returns:
            Domain PullRequest model with PR details.
        """
        repository = self._client.get_repo(f"{owner}/{repo}")
        github_pr = repository.create_pull(
            title=title,
            body=body,
            head=head_branch,
            base=base_branch,
            draft=draft,
        )

        # Convert PyGithub PullRequest to domain model
        # PyGithub state is a string, cast to our Literal type
        state = github_pr.state
        if state not in ("open", "merged", "closed"):
            state = "open"  # Default to open if unexpected state

        return PullRequest(
            number=github_pr.number,
            url=github_pr.html_url,
            head_branch=github_pr.head.ref,
            base_branch=github_pr.base.ref,
            head_sha=github_pr.head.sha,
            created_at=github_pr.created_at,
            state=state,  # type: ignore[arg-type]
        )

    def get_pull_request(self, owner: str, repo: str, pr_number: int) -> PullRequest:
        """Fetch a pull request by repository and PR number.

        Args:
            owner: Repository owner (user or organization).
            repo: Repository name.
            pr_number: Pull request number to fetch.

        Returns:
            Domain PullRequest model with PR details including merge status.
        """
        repository = self._client.get_repo(f"{owner}/{repo}")
        github_pr = repository.get_pull(pr_number)

        # Determine the actual state - PyGithub returns "closed" for merged PRs
        # Check the merged flag to distinguish merged from closed
        if github_pr.merged:
            state = "merged"
        elif github_pr.state == "closed":
            state = "closed"
        else:
            state = "open"

        return PullRequest(
            number=github_pr.number,
            url=github_pr.html_url,
            head_branch=github_pr.head.ref,
            base_branch=github_pr.base.ref,
            head_sha=github_pr.head.sha,
            created_at=github_pr.created_at,
            state=state,  # type: ignore[arg-type]
        )

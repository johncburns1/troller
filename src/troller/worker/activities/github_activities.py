"""GitHub-related Temporal activities.

Activities for fetching and interacting with GitHub issues and pull requests.
"""

from pydantic import BaseModel, ConfigDict, Field
from temporalio import activity

from troller.worker.adapters.github_client import GitHubClient


class FetchIssueInput(BaseModel):
    """Input parameters for fetch_issue activity.

    Attributes:
        repo_owner: GitHub repository owner.
        repo_name: GitHub repository name.
        issue_number: GitHub issue number to fetch.
    """

    model_config = ConfigDict(frozen=True)

    repo_owner: str = Field(..., description="GitHub repository owner")
    repo_name: str = Field(..., description="GitHub repository name")
    issue_number: int = Field(..., description="GitHub issue number to fetch", gt=0)


class FetchIssueOutput(BaseModel):
    """Output from fetch_issue activity.

    Attributes:
        number: Issue number.
        title: Issue title.
        description: Issue description/body.
        labels: List of label names.
        url: Full URL to the issue.
    """

    model_config = ConfigDict(frozen=True)

    number: int = Field(..., description="Issue number", gt=0)
    title: str = Field(..., description="Issue title")
    description: str = Field(..., description="Issue description/body")
    labels: list[str] = Field(..., description="List of label names")
    url: str = Field(..., description="Full URL to the issue")


@activity.defn
async def fetch_issue(input: FetchIssueInput) -> FetchIssueOutput:
    """Fetch issue details from GitHub.

    Args:
        input: Parameters specifying which issue to fetch.

    Returns:
        FetchIssueOutput with issue data retrieved from GitHub.
    """
    client = GitHubClient()
    github_issue = client.get_issue(
        owner=input.repo_owner, repo=input.repo_name, issue_number=input.issue_number
    )

    # Convert PyGithub Issue to activity output
    return FetchIssueOutput(
        number=github_issue.number,
        title=github_issue.title,
        description=github_issue.body or "",
        labels=[label.name for label in github_issue.labels],
        url=github_issue.html_url,
    )


class CreatePullRequestInput(BaseModel):
    """Input parameters for create_pull_request activity.

    Attributes:
        repo_owner: GitHub repository owner.
        repo_name: GitHub repository name.
        title: Pull request title.
        body: Pull request description/body.
        head_branch: Branch containing the changes.
        base_branch: Branch to merge changes into.
        draft: Whether to create as draft PR.
    """

    model_config = ConfigDict(frozen=True)

    repo_owner: str = Field(..., description="GitHub repository owner")
    repo_name: str = Field(..., description="GitHub repository name")
    title: str = Field(..., description="Pull request title")
    body: str = Field(..., description="Pull request description/body")
    head_branch: str = Field(..., description="Branch containing the changes")
    base_branch: str = Field(..., description="Branch to merge changes into")
    draft: bool = Field(default=False, description="Whether to create as draft PR")


class CreatePullRequestOutput(BaseModel):
    """Output from create_pull_request activity.

    Attributes:
        number: Pull request number.
        url: Full URL to the pull request.
        head_branch: Branch containing the changes.
        base_branch: Branch to merge changes into.
        head_sha: SHA of the latest commit in the pull request.
    """

    model_config = ConfigDict(frozen=True)

    number: int = Field(..., description="Pull request number", gt=0)
    url: str = Field(..., description="Full URL to the pull request")
    head_branch: str = Field(..., description="Branch containing the changes")
    base_branch: str = Field(..., description="Branch to merge changes into")
    head_sha: str = Field(..., description="SHA of the latest commit")


@activity.defn
async def create_pull_request(input: CreatePullRequestInput) -> CreatePullRequestOutput:
    """Create a pull request on GitHub.

    Args:
        input: Parameters specifying the pull request details.

    Returns:
        CreatePullRequestOutput with the created pull request details.
    """
    client = GitHubClient()
    pr = client.create_pull_request(
        owner=input.repo_owner,
        repo=input.repo_name,
        title=input.title,
        body=input.body,
        head_branch=input.head_branch,
        base_branch=input.base_branch,
        draft=input.draft,
    )

    # Convert domain model to activity output
    return CreatePullRequestOutput(
        number=pr.number,
        url=pr.url,
        head_branch=pr.head_branch,
        base_branch=pr.base_branch,
        head_sha=pr.head_sha,
    )

"""GitHub-related Temporal activities.

Activities for fetching and interacting with GitHub issues.
"""

from pydantic import BaseModel, ConfigDict, Field
from temporalio import activity

from troller.domain.models.issue import Issue
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


@activity.defn
async def fetch_issue(input: FetchIssueInput) -> Issue:
    """Fetch issue details from GitHub.

    Args:
        input: Parameters specifying which issue to fetch.

    Returns:
        Issue data retrieved from GitHub.
    """
    client = GitHubClient()
    github_issue = client.get_issue(
        owner=input.repo_owner, repo=input.repo_name, issue_number=input.issue_number
    )

    # Convert PyGithub Issue to our Issue dataclass
    return Issue(
        number=github_issue.number,
        title=github_issue.title,
        description=github_issue.body or "",
        labels=[label.name for label in github_issue.labels],
        url=github_issue.html_url,
    )

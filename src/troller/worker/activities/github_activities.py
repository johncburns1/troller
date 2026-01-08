"""GitHub-related Temporal activities.

Activities for fetching and interacting with GitHub issues, pull requests, and branches.
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from temporalio import activity

from troller.worker.adapters.git_operations import GitOperations
from troller.worker.adapters.github_client import GitHubClient
from troller.worker.adapters.repo_cloner import RepoCloner


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


class CreateFeatureBranchInput(BaseModel):
    """Input parameters for create_feature_branch activity.

    Attributes:
        repo_owner: GitHub repository owner.
        repo_name: GitHub repository name.
        branch_name: Name of the new branch to create.
        base_branch: Base branch to branch from (e.g., 'main').
    """

    model_config = ConfigDict(frozen=True)

    repo_owner: str = Field(..., description="GitHub repository owner")
    repo_name: str = Field(..., description="GitHub repository name")
    branch_name: str = Field(..., description="Name of the new branch to create")
    base_branch: str = Field(..., description="Base branch to branch from")


class CreateFeatureBranchOutput(BaseModel):
    """Output from create_feature_branch activity.

    Attributes:
        branch_name: Name of the created branch.
        head_sha: SHA of the branch HEAD commit.
    """

    model_config = ConfigDict(frozen=True)

    branch_name: str = Field(..., description="Name of the created branch")
    head_sha: str = Field(..., description="SHA of the branch HEAD commit")


@activity.defn
async def create_feature_branch(
    input: CreateFeatureBranchInput,
) -> CreateFeatureBranchOutput:
    """Create a feature branch on GitHub.

    This activity clones the base branch, creates a new branch, pushes it to
    the remote repository, and cleans up the temporary directory. It follows
    a self-contained pattern to ensure proper cleanup even if errors occur.

    Args:
        input: Parameters specifying the branch details.

    Returns:
        CreateFeatureBranchOutput with the created branch name and HEAD SHA.

    Raises:
        RuntimeError: If git operations fail.
    """
    repo_cloner = RepoCloner()
    git_operations = GitOperations()

    temp_dir: Path | None = None
    try:
        # Clone base branch to temporary directory
        temp_dir, repo_path, _ = await repo_cloner.clone_to_temp(
            input.repo_owner, input.repo_name, input.base_branch
        )

        # Create new branch from base branch
        await git_operations.create_branch(
            str(repo_path), input.branch_name, input.base_branch
        )

        # Push the new branch to remote with upstream tracking
        await git_operations.push_branch(
            str(repo_path), input.branch_name, force=False, set_upstream=True
        )

        # Get the HEAD commit SHA of the new branch
        head_sha = await git_operations.get_current_sha(str(repo_path))

        return CreateFeatureBranchOutput(
            branch_name=input.branch_name, head_sha=head_sha
        )
    finally:
        # Always cleanup temporary directory, even if errors occurred
        if temp_dir is not None:
            repo_cloner.cleanup(temp_dir)


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

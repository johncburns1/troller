"""Data structures for Temporal workflows.

These structures define inputs and outputs for workflows and activities.
"""

from pydantic import BaseModel, ConfigDict, Field

from troller.worker.activities.activity_outputs import CommitOutput, PlanOutput
from troller.worker.activities.github_activities import CreatePullRequestOutput


class IssueResolutionWorkflowInput(BaseModel):
    """Input parameters for the issue resolution workflow.

    Attributes:
        repo_owner: GitHub repository owner.
        repo_name: GitHub repository name.
        issue_number: GitHub issue number.
        target_branch: Base branch (defaults to main/master if None).
    """

    model_config = ConfigDict(frozen=True)

    repo_owner: str = Field(..., description="GitHub repository owner")
    repo_name: str = Field(..., description="GitHub repository name")
    issue_number: int = Field(..., description="GitHub issue number", gt=0)
    target_branch: str | None = Field(
        default=None, description="Base branch (defaults to main/master if None)"
    )


class IssueResolutionWorkflowOutput(BaseModel):
    """Output from the issue resolution workflow.

    Attributes:
        plan: The generated implementation plan.
        branch_name: Name of the created feature branch.
        commits: List of commits created during implementation.
        pull_request: Pull request created for the changes (if created).
    """

    model_config = ConfigDict(frozen=True)

    plan: PlanOutput = Field(..., description="Generated implementation plan")
    branch_name: str = Field(..., description="Name of the created feature branch")
    commits: list[CommitOutput] = Field(
        ..., description="List of commits created during implementation"
    )
    pull_request: CreatePullRequestOutput | None = Field(
        ..., description="Pull request created for the changes"
    )

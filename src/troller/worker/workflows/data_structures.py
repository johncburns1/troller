"""Data structures for Temporal workflows.

These structures define inputs and outputs for workflows and activities.
"""

from pydantic import BaseModel, ConfigDict, Field


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

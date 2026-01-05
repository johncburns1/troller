"""Data structures for Temporal workflows.

These structures define inputs and outputs for workflows and activities.
"""

from pydantic import BaseModel, ConfigDict, Field


class WorkflowInput(BaseModel):
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


class Issue(BaseModel):
    """GitHub issue data retrieved by fetch_issue activity.

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

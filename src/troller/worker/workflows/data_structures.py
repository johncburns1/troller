"""Data structures for Temporal workflows.

These structures define inputs and outputs for workflows and activities.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowInput:
    """Input parameters for the issue resolution workflow.

    Attributes:
        repo_owner: GitHub repository owner.
        repo_name: GitHub repository name.
        issue_number: GitHub issue number.
        target_branch: Base branch (defaults to main/master if None).
    """

    repo_owner: str
    repo_name: str
    issue_number: int
    target_branch: str | None = None


@dataclass(frozen=True)
class Issue:
    """GitHub issue data retrieved by fetch_issue activity.

    Attributes:
        number: Issue number.
        title: Issue title.
        description: Issue description/body.
        labels: List of label names.
        url: Full URL to the issue.
    """

    number: int
    title: str
    description: str
    labels: list[str]
    url: str

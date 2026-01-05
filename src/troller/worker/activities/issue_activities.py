"""Stubbed activities for GitHub issue operations.

These are placeholder implementations to be replaced with actual logic.
"""

from temporalio import activity

from troller.worker.workflows.data_structures import Issue


@activity.defn
async def fetch_issue(repo_owner: str, repo_name: str, issue_number: int) -> Issue:
    """Fetch issue details from GitHub.

    Args:
        repo_owner: Repository owner.
        repo_name: Repository name.
        issue_number: Issue number.

    Returns:
        Issue data retrieved from GitHub.
    """
    # Stub implementation - returns mock data
    return Issue(
        number=issue_number,
        title=f"Stub Issue #{issue_number}",
        description="This is a stub implementation of the fetch_issue activity.",
        labels=["stub", "test"],
        url=f"https://github.com/{repo_owner}/{repo_name}/issues/{issue_number}",
    )

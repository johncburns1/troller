"""Domain model for GitHub pull requests.

Pure business logic with no external dependencies.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class PullRequest:
    """GitHub pull request state.

    Attributes:
        number: Pull request number.
        url: Full URL to the pull request.
        head_branch: Branch containing the changes (source branch).
        base_branch: Branch to merge changes into (target branch).
        head_sha: SHA of the latest commit in the pull request.
        created_at: When the pull request was created.
        state: Current state of the pull request (open, merged, or closed).
    """

    number: int
    url: str
    head_branch: str
    base_branch: str
    head_sha: str
    created_at: datetime
    state: Literal["open", "merged", "closed"]

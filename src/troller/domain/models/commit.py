"""Domain model for code commits with internal agent review feedback.

Pure business logic with no external dependencies.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class InternalReviewFeedback:
    """Internal review feedback from the Review Agent (AI).

    This is agent-to-agent communication stored in Temporal workflow state only.
    NOT visible on GitHub - distinct from GitHub PR reviews which are public.

    Attributes:
        approved: Whether the Review Agent approved the code for commit.
        comments: Internal review comments for the Coding Agent to address.
        suggested_changes: Specific code changes requested by the Review Agent.
        timestamp: When the internal review was completed.
    """

    approved: bool
    comments: list[str]
    suggested_changes: list[str]
    timestamp: datetime


@dataclass(frozen=True)
class Commit:
    """Code commit with optional internal Review Agent feedback.

    Attributes:
        sha: Git commit SHA (short or full 40-character hash).
        message: Commit message.
        timestamp: When the commit was created.
        internal_review_feedback: Optional feedback from Review Agent (internal only).
    """

    sha: str
    message: str
    timestamp: datetime
    internal_review_feedback: InternalReviewFeedback | None = None

"""GitHub issue domain model.

Pure business logic with no external dependencies.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Issue:
    """GitHub issue data.

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
    labels: list[str] = field(default_factory=list)
    url: str = ""

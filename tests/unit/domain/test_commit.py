"""Unit tests for Commit domain model."""

from datetime import datetime, timezone

import pytest

from troller.domain.models.commit import Commit, InternalReviewFeedback


def test_internal_review_feedback_creation_with_all_fields() -> None:
    """Create InternalReviewFeedback with all fields."""
    timestamp = datetime.now(timezone.utc)
    feedback = InternalReviewFeedback(
        approved=True,
        comments=["Looks good!", "Well tested"],
        suggested_changes=["Add docstring to helper function"],
        timestamp=timestamp,
    )

    assert feedback.approved is True
    assert feedback.comments == ["Looks good!", "Well tested"]
    assert feedback.suggested_changes == ["Add docstring to helper function"]
    assert feedback.timestamp == timestamp


def test_internal_review_feedback_with_empty_lists() -> None:
    """Create InternalReviewFeedback with empty comments and suggested_changes."""
    timestamp = datetime.now(timezone.utc)
    feedback = InternalReviewFeedback(
        approved=True,
        comments=[],
        suggested_changes=[],
        timestamp=timestamp,
    )

    assert feedback.approved is True
    assert feedback.comments == []
    assert feedback.suggested_changes == []
    assert feedback.timestamp == timestamp


def test_internal_review_feedback_not_approved() -> None:
    """Create InternalReviewFeedback with approved=False."""
    timestamp = datetime.now(timezone.utc)
    feedback = InternalReviewFeedback(
        approved=False,
        comments=["Needs refactoring"],
        suggested_changes=[
            "Extract method for better readability",
            "Add error handling",
        ],
        timestamp=timestamp,
    )

    assert feedback.approved is False
    assert len(feedback.comments) == 1
    assert len(feedback.suggested_changes) == 2


def test_internal_review_feedback_immutability() -> None:
    """Verify InternalReviewFeedback instances are immutable."""
    timestamp = datetime.now(timezone.utc)
    feedback = InternalReviewFeedback(
        approved=True,
        comments=["Good work"],
        suggested_changes=[],
        timestamp=timestamp,
    )

    with pytest.raises(AttributeError):
        feedback.approved = False  # type: ignore[misc]


def test_commit_creation_with_required_fields() -> None:
    """Create Commit with only required fields."""
    timestamp = datetime.now(timezone.utc)
    commit = Commit(
        sha="abc123def456",
        message="Add user authentication",
        timestamp=timestamp,
    )

    assert commit.sha == "abc123def456"
    assert commit.message == "Add user authentication"
    assert commit.timestamp == timestamp
    assert commit.internal_review_feedback is None


def test_commit_creation_with_internal_review_feedback() -> None:
    """Create Commit with internal review feedback."""
    commit_timestamp = datetime.now(timezone.utc)
    review_timestamp = datetime.now(timezone.utc)

    feedback = InternalReviewFeedback(
        approved=True,
        comments=["Great implementation"],
        suggested_changes=[],
        timestamp=review_timestamp,
    )

    commit = Commit(
        sha="def456abc789",
        message="Implement JWT token validation",
        timestamp=commit_timestamp,
        internal_review_feedback=feedback,
    )

    assert commit.sha == "def456abc789"
    assert commit.message == "Implement JWT token validation"
    assert commit.timestamp == commit_timestamp
    assert commit.internal_review_feedback is not None
    assert commit.internal_review_feedback.approved is True
    assert commit.internal_review_feedback.comments == ["Great implementation"]


def test_commit_with_full_sha() -> None:
    """Create Commit with full 40-character SHA."""
    timestamp = datetime.now(timezone.utc)
    full_sha = "1234567890abcdef1234567890abcdef12345678"

    commit = Commit(
        sha=full_sha,
        message="Fix authentication bug",
        timestamp=timestamp,
    )

    assert commit.sha == full_sha
    assert len(commit.sha) == 40


def test_commit_with_multiline_message() -> None:
    """Create Commit with multiline commit message."""
    timestamp = datetime.now(timezone.utc)
    message = """Add comprehensive error handling

- Handle network timeouts
- Add retry logic for transient failures
- Log errors with structured logging"""

    commit = Commit(
        sha="abc123",
        message=message,
        timestamp=timestamp,
    )

    assert commit.sha == "abc123"
    assert commit.message == message
    assert "Add comprehensive error handling" in commit.message
    assert "Handle network timeouts" in commit.message


def test_commit_immutability() -> None:
    """Verify Commit instances are immutable."""
    timestamp = datetime.now(timezone.utc)
    commit = Commit(
        sha="abc123",
        message="Test commit",
        timestamp=timestamp,
    )

    with pytest.raises(AttributeError):
        commit.sha = "def456"  # type: ignore[misc]


def test_commit_with_rejected_internal_review() -> None:
    """Create Commit with internal review feedback that is not approved."""
    commit_timestamp = datetime.now(timezone.utc)
    review_timestamp = datetime.now(timezone.utc)

    feedback = InternalReviewFeedback(
        approved=False,
        comments=["Needs improvement", "Consider edge cases"],
        suggested_changes=[
            "Add input validation",
            "Handle empty string case",
            "Add unit tests for error paths",
        ],
        timestamp=review_timestamp,
    )

    commit = Commit(
        sha="xyz789",
        message="Initial implementation",
        timestamp=commit_timestamp,
        internal_review_feedback=feedback,
    )

    assert commit.internal_review_feedback is not None
    assert commit.internal_review_feedback.approved is False
    assert len(commit.internal_review_feedback.comments) == 2
    assert len(commit.internal_review_feedback.suggested_changes) == 3

"""Unit tests for PullRequest domain model."""

from datetime import datetime, timezone

import pytest

from troller.domain.models.pull_request import PullRequest


def test_pull_request_creation_with_all_fields() -> None:
    """Create PullRequest with all fields."""
    created_at = datetime.now(timezone.utc)
    pr = PullRequest(
        number=42,
        url="https://github.com/owner/repo/pull/42",
        head_sha="abc123def456",
        created_at=created_at,
        state="open",
    )

    assert pr.number == 42
    assert pr.url == "https://github.com/owner/repo/pull/42"
    assert pr.head_sha == "abc123def456"
    assert pr.created_at == created_at
    assert pr.state == "open"


def test_pull_request_with_state_merged() -> None:
    """Create PullRequest with state='merged'."""
    created_at = datetime.now(timezone.utc)
    pr = PullRequest(
        number=100,
        url="https://github.com/owner/repo/pull/100",
        head_sha="1234567890abcdef1234567890abcdef12345678",
        created_at=created_at,
        state="merged",
    )

    assert pr.number == 100
    assert pr.state == "merged"
    assert len(pr.head_sha) == 40


def test_pull_request_with_state_closed() -> None:
    """Create PullRequest with state='closed'."""
    created_at = datetime.now(timezone.utc)
    pr = PullRequest(
        number=55,
        url="https://github.com/owner/repo/pull/55",
        head_sha="def456",
        created_at=created_at,
        state="closed",
    )

    assert pr.number == 55
    assert pr.state == "closed"


def test_pull_request_immutability() -> None:
    """Verify PullRequest instances are immutable."""
    created_at = datetime.now(timezone.utc)
    pr = PullRequest(
        number=1,
        url="https://github.com/owner/repo/pull/1",
        head_sha="abc123",
        created_at=created_at,
        state="open",
    )

    with pytest.raises(AttributeError):
        pr.state = "merged"  # type: ignore[misc]


def test_pull_request_with_different_pr_numbers() -> None:
    """Create multiple PullRequests with different numbers."""
    created_at = datetime.now(timezone.utc)

    pr1 = PullRequest(
        number=1,
        url="https://github.com/owner/repo/pull/1",
        head_sha="sha1",
        created_at=created_at,
        state="open",
    )

    pr2 = PullRequest(
        number=9999,
        url="https://github.com/owner/repo/pull/9999",
        head_sha="sha2",
        created_at=created_at,
        state="merged",
    )

    assert pr1.number == 1
    assert pr2.number == 9999
    assert pr1.state == "open"
    assert pr2.state == "merged"


def test_pull_request_url_formats() -> None:
    """Create PullRequest with different URL formats."""
    created_at = datetime.now(timezone.utc)

    # Standard GitHub URL
    pr1 = PullRequest(
        number=42,
        url="https://github.com/owner/repo/pull/42",
        head_sha="abc123",
        created_at=created_at,
        state="open",
    )

    # GitHub Enterprise URL
    pr2 = PullRequest(
        number=10,
        url="https://github.enterprise.com/owner/repo/pull/10",
        head_sha="def456",
        created_at=created_at,
        state="open",
    )

    assert "github.com" in pr1.url
    assert "github.enterprise.com" in pr2.url
    assert pr1.number == 42
    assert pr2.number == 10


def test_pull_request_with_short_and_full_sha() -> None:
    """Create PullRequest with both short and full SHA formats."""
    created_at = datetime.now(timezone.utc)

    # Short SHA
    pr_short = PullRequest(
        number=1,
        url="https://github.com/owner/repo/pull/1",
        head_sha="abc123",
        created_at=created_at,
        state="open",
    )

    # Full SHA
    pr_full = PullRequest(
        number=2,
        url="https://github.com/owner/repo/pull/2",
        head_sha="1234567890abcdef1234567890abcdef12345678",
        created_at=created_at,
        state="open",
    )

    assert pr_short.head_sha == "abc123"
    assert pr_full.head_sha == "1234567890abcdef1234567890abcdef12345678"
    assert len(pr_short.head_sha) == 6
    assert len(pr_full.head_sha) == 40

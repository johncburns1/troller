"""Unit tests for Plan domain model."""

from datetime import datetime, timezone

import pytest

from troller.domain.models.plan import Plan, PlanStep


def test_plan_step_creation() -> None:
    """Create a PlanStep with all fields."""
    step = PlanStep(
        id="step-1",
        description="Implement feature X",
        completed=False,
    )

    assert step.id == "step-1"
    assert step.description == "Implement feature X"
    assert step.completed is False


def test_plan_step_creation_completed() -> None:
    """Create a completed PlanStep."""
    step = PlanStep(
        id="step-1",
        description="Implement feature X",
        completed=True,
    )

    assert step.id == "step-1"
    assert step.description == "Implement feature X"
    assert step.completed is True


def test_plan_creation_with_required_fields() -> None:
    """Create a Plan with only required fields."""
    created_at = datetime.now(timezone.utc)
    steps = [
        PlanStep(id="step-1", description="First step", completed=False),
        PlanStep(id="step-2", description="Second step", completed=False),
    ]

    plan = Plan(
        summary="Implement user authentication",
        steps=steps,
        created_at=created_at,
        metadata={},
    )

    assert plan.summary == "Implement user authentication"
    assert len(plan.steps) == 2
    assert plan.steps[0].id == "step-1"
    assert plan.created_at == created_at
    assert plan.metadata == {}


def test_plan_creation_with_rich_metadata() -> None:
    """Create a Plan with rich metadata from skill execution."""
    created_at = datetime.now(timezone.utc)
    steps = [
        PlanStep(
            id="step-1",
            description="Set up database models",
            completed=False,
        ),
    ]

    plan = Plan(
        summary="Implement user authentication",
        steps=steps,
        created_at=created_at,
        metadata={
            "issue_number": 42,
            "repo": "test/repo",
            "skill_output": "Full plan text from skill execution...",
        },
    )

    assert plan.summary == "Implement user authentication"
    assert len(plan.steps) == 1
    assert plan.metadata == {
        "issue_number": 42,
        "repo": "test/repo",
        "skill_output": "Full plan text from skill execution...",
    }


def test_plan_step_immutability() -> None:
    """Verify PlanStep instances are immutable."""
    step = PlanStep(
        id="step-1",
        description="Test step",
        completed=False,
    )

    with pytest.raises(AttributeError):
        step.completed = True  # type: ignore[misc]


def test_plan_immutability() -> None:
    """Verify Plan instances are immutable."""
    plan = Plan(
        summary="Test plan",
        steps=[],
        created_at=datetime.now(timezone.utc),
        metadata={},
    )

    with pytest.raises(AttributeError):
        plan.summary = "Changed"  # type: ignore[misc]

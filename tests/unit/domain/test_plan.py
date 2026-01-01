"""Unit tests for Plan domain model."""

from datetime import datetime, timezone

import pytest

from troller.domain.models.plan import Plan, PlanStep


def test_plan_step_creation_with_required_fields() -> None:
    """Create a PlanStep with only required fields."""
    step = PlanStep(
        id="step-1",
        description="Implement feature X",
        completed=False,
    )

    assert step.id == "step-1"
    assert step.description == "Implement feature X"
    assert step.completed is False
    assert step.related_files is None
    assert step.estimated_complexity is None


def test_plan_step_creation_with_all_fields() -> None:
    """Create a PlanStep with all optional fields."""
    step = PlanStep(
        id="step-1",
        description="Implement feature X",
        completed=True,
        related_files=["src/main.py", "tests/test_main.py"],
        estimated_complexity="moderate",
    )

    assert step.id == "step-1"
    assert step.description == "Implement feature X"
    assert step.completed is True
    assert step.related_files == ["src/main.py", "tests/test_main.py"]
    assert step.estimated_complexity == "moderate"


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
    assert plan.technical_approach is None
    assert plan.testing_strategy is None
    assert plan.metadata == {}


def test_plan_creation_with_all_fields() -> None:
    """Create a Plan with all optional fields."""
    created_at = datetime.now(timezone.utc)
    steps = [
        PlanStep(
            id="step-1",
            description="Set up database models",
            completed=False,
            related_files=["src/models/user.py"],
            estimated_complexity="simple",
        ),
    ]

    plan = Plan(
        summary="Implement user authentication",
        steps=steps,
        created_at=created_at,
        metadata={"issue_number": 42, "repo": "test/repo"},
        technical_approach="Use JWT tokens with refresh token rotation",
        testing_strategy="Unit tests for token generation, integration tests for auth flow",
    )

    assert plan.summary == "Implement user authentication"
    assert len(plan.steps) == 1
    assert plan.technical_approach == "Use JWT tokens with refresh token rotation"
    assert plan.testing_strategy == (
        "Unit tests for token generation, integration tests for auth flow"
    )
    assert plan.metadata == {"issue_number": 42, "repo": "test/repo"}


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


def test_plan_step_complexity_values() -> None:
    """Verify PlanStep accepts valid complexity values."""
    valid_complexities = ["simple", "moderate", "complex"]

    for complexity in valid_complexities:
        step = PlanStep(
            id="step-1",
            description="Test",
            completed=False,
            estimated_complexity=complexity,  # type: ignore[arg-type]
        )
        assert step.estimated_complexity == complexity

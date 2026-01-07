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
    assert step.related_files == []
    assert step.estimated_complexity is None


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
    assert step.related_files == []
    assert step.estimated_complexity is None


def test_plan_step_with_related_files() -> None:
    """Create a PlanStep with related files."""
    step = PlanStep(
        id="step-1",
        description="Update authentication logic",
        completed=False,
        related_files=["src/auth/login.py", "tests/test_auth.py"],
    )

    assert step.id == "step-1"
    assert step.related_files == ["src/auth/login.py", "tests/test_auth.py"]


def test_plan_step_with_complexity() -> None:
    """Create a PlanStep with estimated complexity."""
    step = PlanStep(
        id="step-1",
        description="Refactor database layer",
        completed=False,
        estimated_complexity="complex",
    )

    assert step.id == "step-1"
    assert step.estimated_complexity == "complex"


def test_plan_step_with_all_optional_fields() -> None:
    """Create a PlanStep with all optional fields populated."""
    step = PlanStep(
        id="step-2",
        description="Add validation",
        completed=False,
        related_files=["src/validators.py"],
        estimated_complexity="simple",
    )

    assert step.id == "step-2"
    assert step.description == "Add validation"
    assert step.completed is False
    assert step.related_files == ["src/validators.py"]
    assert step.estimated_complexity == "simple"


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
    )

    assert plan.summary == "Implement user authentication"
    assert len(plan.steps) == 2
    assert plan.steps[0].id == "step-1"
    assert plan.created_at == created_at
    assert plan.technical_approach is None
    assert plan.testing_strategy is None
    assert plan.metadata == {}


def test_plan_creation_with_technical_details() -> None:
    """Create a Plan with technical approach and testing strategy."""
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
        technical_approach="Use hexagonal architecture with JWT tokens",
        testing_strategy="Unit tests for domain logic, integration tests for auth flow",
    )

    assert plan.summary == "Implement user authentication"
    assert len(plan.steps) == 1
    assert plan.technical_approach == "Use hexagonal architecture with JWT tokens"
    assert (
        plan.testing_strategy
        == "Unit tests for domain logic, integration tests for auth flow"
    )


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
        },
    )

    assert plan.summary == "Implement user authentication"
    assert len(plan.steps) == 1
    assert plan.metadata == {
        "issue_number": 42,
        "repo": "test/repo",
    }


def test_plan_with_all_fields() -> None:
    """Create a Plan with all optional fields populated."""
    created_at = datetime.now(timezone.utc)
    steps = [
        PlanStep(
            id="step-1",
            description="Implement auth endpoints",
            completed=False,
            related_files=["src/api/auth.py"],
            estimated_complexity="moderate",
        ),
    ]

    plan = Plan(
        summary="Add JWT authentication",
        steps=steps,
        created_at=created_at,
        technical_approach="Use PyJWT library with refresh tokens",
        testing_strategy="Unit tests for token generation, integration tests for endpoints",
        metadata={"issue_number": 123},
    )

    assert plan.summary == "Add JWT authentication"
    assert plan.technical_approach == "Use PyJWT library with refresh tokens"
    assert (
        plan.testing_strategy
        == "Unit tests for token generation, integration tests for endpoints"
    )
    assert plan.steps[0].related_files == ["src/api/auth.py"]
    assert plan.steps[0].estimated_complexity == "moderate"
    assert plan.metadata["issue_number"] == 123


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
    )

    with pytest.raises(AttributeError):
        plan.summary = "Changed"  # type: ignore[misc]


def test_plan_creation_with_based_on_commit() -> None:
    """Create a Plan with based_on_commit field."""
    created_at = datetime.now(timezone.utc)
    commit_sha = "abc123def456789012345678901234567890abcd"

    plan = Plan(
        summary="Implement feature X",
        steps=[],
        created_at=created_at,
        based_on_commit=commit_sha,
    )

    assert plan.summary == "Implement feature X"
    assert plan.based_on_commit == commit_sha
    assert plan.created_at == created_at


def test_plan_creation_without_based_on_commit() -> None:
    """Create a Plan without based_on_commit field (should default to None)."""
    created_at = datetime.now(timezone.utc)

    plan = Plan(
        summary="Implement feature Y",
        steps=[],
        created_at=created_at,
    )

    assert plan.summary == "Implement feature Y"
    assert plan.based_on_commit is None


def test_plan_with_all_fields_including_commit() -> None:
    """Create a Plan with all fields including based_on_commit."""
    created_at = datetime.now(timezone.utc)
    commit_sha = "1234567890abcdef1234567890abcdef12345678"
    steps = [
        PlanStep(
            id="step-1",
            description="Implement component",
            completed=False,
            related_files=["src/component.py"],
            estimated_complexity="moderate",
        ),
    ]

    plan = Plan(
        summary="Add new feature with commit tracking",
        steps=steps,
        created_at=created_at,
        technical_approach="Use hexagonal architecture",
        testing_strategy="TDD with unit tests",
        metadata={"issue_number": 27},
        based_on_commit=commit_sha,
    )

    assert plan.summary == "Add new feature with commit tracking"
    assert plan.based_on_commit == commit_sha
    assert plan.technical_approach == "Use hexagonal architecture"
    assert plan.testing_strategy == "TDD with unit tests"
    assert plan.metadata["issue_number"] == 27
    assert len(plan.steps) == 1

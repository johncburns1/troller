"""Tests for TDD response Pydantic models."""

from troller.worker.services.planning_models import (
    FileOperationResponse,
    VerificationResponse,
    TDDSubstepResponse,
    PlanStepResponse,
    PlanResponse,
)


def test_file_operation_response_create():
    op = FileOperationResponse(
        operation="create",
        file_path="src/auth/jwt.py",
        description="Create JWT adapter",
    )
    assert op.operation == "create"
    assert op.line_range is None
    assert op.code_snippet is None


def test_file_operation_response_modify():
    op = FileOperationResponse(
        operation="modify",
        file_path="src/auth/jwt.py",
        line_range="45-67",
        description="Add validation",
        code_snippet="def validate(): pass",
    )
    assert op.line_range == "45-67"


def test_verification_response_defaults():
    v = VerificationResponse(
        command="pytest tests/",
        expected_outcome="pass",
    )
    assert v.timeout_seconds == 120
    assert v.expected_text is None


def test_tdd_substep_response():
    substep = TDDSubstepResponse(
        id="step-1.1",
        phase="write_test",
        description="Write failing test",
    )
    assert substep.file_operations == []
    assert substep.verification is None
    assert substep.completed is False


def test_plan_step_response_with_substeps():
    substep = TDDSubstepResponse(
        id="step-1.1",
        phase="write_test",
        description="Write test",
    )
    step = PlanStepResponse(
        id="step-1",
        description="Implement feature",
        substeps=[substep],
        commit_message_template="feat: add feature",
    )
    assert len(step.substeps) == 1


def test_plan_step_response_backwards_compatible():
    """Existing schemas without substeps should still validate."""
    step = PlanStepResponse(
        id="step-1",
        description="Simple step",
    )
    assert step.substeps == []
    assert step.commit_message_template is None


def test_plan_response_json_schema_includes_substeps():
    schema = PlanResponse.model_json_schema()
    # Verify substeps are in the schema
    assert "TDDSubstepResponse" in str(schema)

"""Tests for activity output models."""

from troller.worker.activities.activity_outputs import (
    FileOperationOutput,
    VerificationOutput,
    TDDSubstepOutput,
    PlanStepOutput,
)


def test_file_operation_output():
    op = FileOperationOutput(
        operation="create",
        file_path="src/auth.py",
        description="Create auth module",
    )
    assert op.operation == "create"


def test_tdd_substep_output():
    substep = TDDSubstepOutput(
        id="step-1.1",
        phase="write_test",
        description="Write test",
    )
    assert substep.completed is False


def test_plan_step_output_with_substeps():
    substep = TDDSubstepOutput(
        id="step-1.1",
        phase="write_test",
        description="Write test",
    )
    step = PlanStepOutput(
        id="step-1",
        description="Feature",
        substeps=[substep],
    )
    assert len(step.substeps) == 1


def test_plan_step_output_backwards_compatible():
    step = PlanStepOutput(
        id="step-1",
        description="Simple step",
    )
    assert step.substeps == []

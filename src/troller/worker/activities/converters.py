"""DTO ↔ Domain model conversion utilities.

Centralized conversion functions to eliminate duplication across activities.
"""

from typing import Literal, cast

from troller.domain.models.commit import Commit
from troller.domain.models.issue import Issue
from troller.domain.models.plan import (
    FileOperation,
    Plan,
    PlanStep,
    TDDSubstep,
    Verification,
)
from troller.worker.activities.activity_outputs import (
    CommitOutput,
    FileOperationOutput,
    PlanOutput,
    PlanStepOutput,
    TDDSubstepOutput,
    VerificationOutput,
)

# Type aliases for domain model literal types
FileOperationType = Literal["create", "modify", "delete", "test"]
TDDPhaseType = Literal[
    "write_test", "verify_fails", "implement", "verify_passes", "refactor", "commit"
]
VerificationOutcomeType = Literal["pass", "fail", "output_contains"]


def plan_output_to_domain(plan_output: PlanOutput) -> Plan:
    """Convert PlanOutput DTO to Plan domain model with full fidelity.

    Preserves all nested data including substeps, preconditions, and
    verification commands that are critical for TDD workflow execution.

    Args:
        plan_output: The activity output DTO to convert.

    Returns:
        Plan domain model with complete data.
    """
    steps = []
    for step_output in plan_output.steps:
        # Convert substeps with full fidelity
        substeps = [
            _substep_output_to_domain(substep) for substep in step_output.substeps
        ]

        # Convert preconditions
        preconditions = [
            _verification_output_to_domain(precondition)
            for precondition in step_output.preconditions
        ]

        steps.append(
            PlanStep(
                id=step_output.id,
                description=step_output.description,
                completed=step_output.completed,
                related_files=step_output.related_files,
                estimated_complexity=step_output.estimated_complexity,
                substeps=substeps,
                commit_message_template=step_output.commit_message_template,
                depends_on=step_output.depends_on,
                preconditions=preconditions,
            )
        )

    return Plan(
        summary=plan_output.summary,
        steps=steps,
        created_at=plan_output.created_at,
        technical_approach=plan_output.technical_approach,
        testing_strategy=plan_output.testing_strategy,
        metadata=plan_output.metadata,
        based_on_commit=plan_output.based_on_commit,
    )


def _substep_output_to_domain(substep_output: TDDSubstepOutput) -> TDDSubstep:
    """Convert TDDSubstepOutput DTO to TDDSubstep domain model."""
    file_ops = [
        FileOperation(
            operation=cast(FileOperationType, op.operation),
            file_path=op.file_path,
            description=op.description,
            line_range=op.line_range,
            code_snippet=op.code_snippet,
        )
        for op in substep_output.file_operations
    ]

    verification = None
    if substep_output.verification:
        verification = _verification_output_to_domain(substep_output.verification)

    return TDDSubstep(
        id=substep_output.id,
        phase=cast(TDDPhaseType, substep_output.phase),
        description=substep_output.description,
        file_operations=file_ops,
        verification=verification,
        code_hints=substep_output.code_hints,
        completed=substep_output.completed,
        result=substep_output.result,
    )


def _verification_output_to_domain(
    verification_output: VerificationOutput,
) -> Verification:
    """Convert VerificationOutput DTO to Verification domain model."""
    return Verification(
        command=verification_output.command,
        expected_outcome=cast(
            VerificationOutcomeType, verification_output.expected_outcome
        ),
        expected_text=verification_output.expected_text,
        timeout_seconds=verification_output.timeout_seconds,
    )


def issue_from_activity_input(
    number: int,
    title: str,
    description: str,
    labels: list[str],
    url: str,
) -> Issue:
    """Create Issue domain model from activity input primitives.

    Args:
        number: GitHub issue number.
        title: Issue title.
        description: Issue description/body.
        labels: List of label names.
        url: Full URL to the issue.

    Returns:
        Issue domain model.
    """
    return Issue(
        number=number,
        title=title,
        description=description,
        labels=labels,
        url=url,
    )


def commit_output_to_domain(commit_output: CommitOutput) -> Commit:
    """Convert CommitOutput DTO to Commit domain model.

    Args:
        commit_output: The activity output DTO to convert.

    Returns:
        Commit domain model.
    """
    return Commit(
        sha=commit_output.sha,
        message=commit_output.message,
        timestamp=commit_output.timestamp,
        internal_review_feedback=None,
    )


def plan_step_output_to_domain(step_output: PlanStepOutput) -> PlanStep:
    """Convert PlanStepOutput DTO to PlanStep domain model.

    Args:
        step_output: The activity output DTO to convert.

    Returns:
        PlanStep domain model with full data.
    """
    substeps = [_substep_output_to_domain(substep) for substep in step_output.substeps]
    preconditions = [
        _verification_output_to_domain(precondition)
        for precondition in step_output.preconditions
    ]

    return PlanStep(
        id=step_output.id,
        description=step_output.description,
        completed=step_output.completed,
        related_files=step_output.related_files,
        estimated_complexity=step_output.estimated_complexity,
        substeps=substeps,
        commit_message_template=step_output.commit_message_template,
        depends_on=step_output.depends_on,
        preconditions=preconditions,
    )


def file_operation_output_to_domain(op_output: FileOperationOutput) -> FileOperation:
    """Convert FileOperationOutput DTO to FileOperation domain model.

    Args:
        op_output: The activity output DTO to convert.

    Returns:
        FileOperation domain model.
    """
    return FileOperation(
        operation=cast(FileOperationType, op_output.operation),
        file_path=op_output.file_path,
        description=op_output.description,
        line_range=op_output.line_range,
        code_snippet=op_output.code_snippet,
    )

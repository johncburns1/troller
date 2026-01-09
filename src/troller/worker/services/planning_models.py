"""Pydantic models for plan generation responses.

These models define the structure for LLM-generated implementation plans.
Used for structured output validation when generating plans via Claude Agent SDK.
"""

from typing import Literal

from pydantic import BaseModel, Field


class FileOperationResponse(BaseModel):
    """File operation specification for structured output."""

    operation: Literal["create", "modify", "delete", "test"] = Field(
        ..., description="Type of file operation"
    )
    file_path: str = Field(..., description="Full path to file")
    description: str = Field(..., description="What this operation does")
    line_range: str | None = Field(
        default=None, description="Line range for modify operations (e.g., '45-67')"
    )
    code_snippet: str | None = Field(
        default=None, description="Code to insert or change"
    )


class VerificationResponse(BaseModel):
    """Verification command specification for structured output."""

    command: str = Field(..., description="Command to run for verification")
    expected_outcome: Literal["pass", "fail", "output_contains"] = Field(
        ..., description="Expected result of the command"
    )
    expected_text: str | None = Field(
        default=None, description="Text to check for in output"
    )
    timeout_seconds: int = Field(default=120, description="Command timeout")


class TDDSubstepResponse(BaseModel):
    """TDD substep for granular execution tracking."""

    id: str = Field(..., description="Substep ID (e.g., 'step-1.1')")
    phase: Literal[
        "write_test", "verify_fails", "implement", "verify_passes", "refactor", "commit"
    ] = Field(..., description="TDD phase this substep represents")
    description: str = Field(..., description="What this substep does")
    file_operations: list[FileOperationResponse] = Field(
        default_factory=list, description="File operations in this substep"
    )
    verification: VerificationResponse | None = Field(
        default=None, description="Verification to run after substep"
    )
    code_hints: dict[str, str] = Field(
        default_factory=dict, description="Code snippets keyed by filename"
    )
    completed: bool = Field(default=False, description="Whether substep is done")
    result: str | None = Field(default=None, description="Execution result")


class PlanStepResponse(BaseModel):
    """Pydantic model for LLM-generated plan step (structured output).

    This model defines the schema for individual plan steps returned by
    the planning agent via Claude Agent SDK structured outputs.
    """

    id: str = Field(..., description="Unique identifier for the step (e.g., 'step-1')")
    description: str = Field(..., description="Detailed description of the step")
    completed: bool = Field(default=False, description="Whether this step is completed")
    related_files: list[str] = Field(
        default_factory=list, description="Files that will be modified in this step"
    )
    estimated_complexity: Literal["simple", "moderate", "complex"] | None = Field(
        default=None, description="Estimated complexity of the step"
    )
    substeps: list[TDDSubstepResponse] = Field(
        default_factory=list, description="TDD substeps for granular execution"
    )
    commit_message_template: str | None = Field(
        default=None, description="Git commit message template"
    )
    depends_on: list[str] = Field(
        default_factory=list, description="IDs of steps this depends on"
    )
    preconditions: list[VerificationResponse] = Field(
        default_factory=list, description="Conditions to verify before starting"
    )


class PlanResponse(BaseModel):
    """Pydantic model for LLM-generated plan (structured output).

    This model defines the schema for the complete implementation plan
    returned by the planning agent via Claude Agent SDK structured outputs.
    It will be automatically validated against the JSON schema during
    agent execution.
    """

    summary: str = Field(..., description="High-level summary of what needs to be done")
    steps: list[PlanStepResponse] = Field(
        ..., min_length=1, description="Ordered list of implementation steps"
    )
    technical_approach: str | None = Field(
        default=None, description="Architecture decisions, libraries, patterns to use"
    )
    testing_strategy: str | None = Field(
        default=None, description="How to test the implementation"
    )

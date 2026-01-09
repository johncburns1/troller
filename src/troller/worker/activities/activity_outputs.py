"""Output models for Temporal activities.

These Pydantic models define the structure of data returned from activities.
They serve as the serialization boundary between activities and workflows.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FileOperationOutput(BaseModel):
    """Serializable file operation for Temporal.

    Attributes:
        operation: Type of operation (create, modify, delete, etc.).
        file_path: Path to the file being operated on.
        description: Human-readable description of the operation.
        line_range: Optional line range for modifications.
        code_snippet: Optional code snippet for the operation.
    """

    model_config = ConfigDict(frozen=True)

    operation: str = Field(..., description="Operation type")
    file_path: str = Field(..., description="File path")
    description: str = Field(..., description="Operation description")
    line_range: str | None = Field(default=None, description="Line range")
    code_snippet: str | None = Field(default=None, description="Code snippet")


class VerificationOutput(BaseModel):
    """Serializable verification command for Temporal.

    Attributes:
        command: The command to run for verification.
        expected_outcome: Description of what success looks like.
        expected_text: Optional text to look for in output.
        timeout_seconds: Timeout for the verification command.
    """

    model_config = ConfigDict(frozen=True)

    command: str = Field(..., description="Verification command")
    expected_outcome: str = Field(..., description="Expected outcome")
    expected_text: str | None = Field(
        default=None, description="Expected text in output"
    )
    timeout_seconds: int = Field(default=120, description="Timeout in seconds")


class TDDSubstepOutput(BaseModel):
    """Serializable TDD substep for Temporal.

    Attributes:
        id: Unique identifier for the substep.
        phase: TDD phase (write_test, run_test_fail, implement, run_test_pass, refactor).
        description: Human-readable description of the substep.
        file_operations: List of file operations for this substep.
        verification: Optional verification command.
        code_hints: Hints for implementation.
        completed: Whether this substep has been completed.
        result: Optional result from completing the substep.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Substep identifier")
    phase: str = Field(..., description="TDD phase")
    description: str = Field(..., description="Substep description")
    file_operations: list[FileOperationOutput] = Field(
        default_factory=list, description="File operations"
    )
    verification: VerificationOutput | None = Field(
        default=None, description="Verification command"
    )
    code_hints: dict[str, str] = Field(default_factory=dict, description="Code hints")
    completed: bool = Field(default=False, description="Whether substep is completed")
    result: str | None = Field(default=None, description="Substep result")


class PlanStepOutput(BaseModel):
    """Represents a single implementation plan step.

    Attributes:
        id: Unique identifier for the step (e.g., 'step-1', 'step-2').
        description: What this step entails.
        completed: Whether this step has been completed.
        related_files: Files that will be modified in this step.
        estimated_complexity: Estimated complexity level of this step.
        substeps: TDD substeps for this step.
        commit_message_template: Template for commit message.
        depends_on: List of step IDs this step depends on.
        preconditions: Verification commands to run before this step.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique step identifier")
    description: str = Field(..., description="Step description")
    completed: bool = Field(default=False, description="Whether step is completed")
    related_files: list[str] = Field(default_factory=list, description="Related files")
    estimated_complexity: Literal["simple", "moderate", "complex"] | None = Field(
        default=None, description="Estimated complexity"
    )
    substeps: list[TDDSubstepOutput] = Field(
        default_factory=list, description="TDD substeps"
    )
    commit_message_template: str | None = Field(
        default=None, description="Commit message template"
    )
    depends_on: list[str] = Field(default_factory=list, description="Step dependencies")
    preconditions: list[VerificationOutput] = Field(
        default_factory=list, description="Precondition verifications"
    )


class ToolInvocationOutput(BaseModel):
    """Represents a single tool invocation record.

    Attributes:
        tool: Name of the tool (Bash, Skill, Read, Grep, Glob, etc.).
        details: Human-readable description of what the tool did.
        parameters: Key parameters from the tool invocation for audit trail.
    """

    model_config = ConfigDict(frozen=True)

    tool: str = Field(..., description="Tool name")
    details: str = Field(..., description="What the tool did")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )


class LLMMetadataOutput(BaseModel):
    """LLM execution metadata for observability and cost tracking.

    Attributes:
        total_cost_usd: Total cost of the LLM execution in USD.
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.
        duration_ms: Total execution duration in milliseconds.
        duration_api_ms: Time spent in API calls in milliseconds.
        num_turns: Number of conversation turns.
        model: Claude model used for execution.
        tools_used: List of all tools used during execution.
        execution_flow: Brief summary of execution approach.
        tool_invocations: Detailed audit trail of all tool invocations.
    """

    model_config = ConfigDict(frozen=True)

    total_cost_usd: float | None = Field(None, description="Total cost in USD")
    input_tokens: int | None = Field(None, description="Input tokens")
    output_tokens: int | None = Field(None, description="Output tokens")
    duration_ms: int = Field(..., description="Total duration in ms")
    duration_api_ms: int = Field(..., description="API duration in ms")
    num_turns: int = Field(..., description="Number of turns")
    model: str | None = Field(None, description="Model used")
    tools_used: list[str] = Field(default_factory=list, description="Tools used")
    execution_flow: str = Field(default="", description="Execution flow summary")
    tool_invocations: list[ToolInvocationOutput] = Field(
        default_factory=list, description="Tool invocation audit trail"
    )


class PlanOutput(BaseModel):
    """Implementation plan structure.

    Attributes:
        summary: High-level description of the plan.
        steps: Ordered list of implementation steps.
        created_at: When this plan was created.
        technical_approach: Architecture decisions, libraries, and patterns to use.
        testing_strategy: How to test the implementation.
        metadata: Extensible metadata for additional context.
        based_on_commit: Git commit SHA the plan was based on.
    """

    model_config = ConfigDict(frozen=True)

    summary: str = Field(..., description="Plan summary")
    steps: list[PlanStepOutput] = Field(..., description="Implementation steps")
    created_at: datetime = Field(..., description="Creation timestamp")
    technical_approach: str | None = Field(None, description="Technical approach")
    testing_strategy: str | None = Field(None, description="Testing strategy")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")
    based_on_commit: str | None = Field(None, description="Based on commit SHA")


class InternalReviewFeedbackOutput(BaseModel):
    """Internal review feedback from Review Agent.

    Attributes:
        approved: Whether the Review Agent approved the code.
        comments: Internal review comments.
        suggested_changes: Specific code changes requested.
        timestamp: When the review was completed.
    """

    model_config = ConfigDict(frozen=True)

    approved: bool = Field(..., description="Approval status")
    comments: list[str] = Field(default_factory=list, description="Review comments")
    suggested_changes: list[str] = Field(
        default_factory=list, description="Suggested changes"
    )
    timestamp: datetime = Field(..., description="Review timestamp")


class CommitOutput(BaseModel):
    """Code commit with optional internal review feedback.

    Attributes:
        sha: Git commit SHA.
        message: Commit message.
        timestamp: When the commit was created.
        internal_review_feedback: Optional Review Agent feedback.
    """

    model_config = ConfigDict(frozen=True)

    sha: str = Field(..., description="Git commit SHA")
    message: str = Field(..., description="Commit message")
    timestamp: datetime = Field(..., description="Commit timestamp")
    internal_review_feedback: InternalReviewFeedbackOutput | None = Field(
        None, description="Internal review feedback"
    )

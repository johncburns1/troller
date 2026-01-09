"""Planning-related Temporal activities.

Activities for AI-powered implementation planning.
"""

from pydantic import BaseModel, ConfigDict, Field
from temporalio import activity

from troller.config import config
from troller.worker.activities.activity_outputs import (
    FileOperationOutput,
    LLMMetadataOutput,
    PlanOutput,
    PlanStepOutput,
    TDDSubstepOutput,
    VerificationOutput,
)
from troller.worker.adapters.claude_client import ClaudeClient
from troller.worker.adapters.repo_cloner import RepoCloner
from troller.worker.services.planning_service import PlanningService


class PlanningInput(BaseModel):
    """Input parameters for run_planning_agent activity.

    Attributes:
        issue_number: GitHub issue number.
        issue_title: GitHub issue title.
        issue_description: GitHub issue description/body.
        issue_labels: List of label names.
        issue_url: Full URL to the issue.
        repo_owner: GitHub repository owner.
        repo_name: GitHub repository name.
        target_branch: Branch to analyze (defaults to main/master if None).
    """

    model_config = ConfigDict(frozen=True)

    issue_number: int = Field(..., description="GitHub issue number", gt=0)
    issue_title: str = Field(..., description="GitHub issue title")
    issue_description: str = Field(..., description="GitHub issue description/body")
    issue_labels: list[str] = Field(
        default_factory=list, description="List of label names"
    )
    issue_url: str = Field(default="", description="Full URL to the issue")
    repo_owner: str = Field(..., description="GitHub repository owner")
    repo_name: str = Field(..., description="GitHub repository name")
    target_branch: str | None = Field(
        default=None, description="Branch to analyze (defaults to main/master if None)"
    )


class PlanningActivityOutput(BaseModel):
    """Output from run_planning_agent activity.

    Attributes:
        plan: The generated implementation plan.
        llm_metadata: Metadata from LLM execution (cost, tokens, tools used, etc.).
    """

    model_config = ConfigDict(frozen=True)

    plan: PlanOutput = Field(..., description="Generated implementation plan")
    llm_metadata: LLMMetadataOutput = Field(
        ..., description="LLM execution metadata for observability"
    )


@activity.defn
async def run_planning_agent(input: PlanningInput) -> PlanningActivityOutput:
    """Run the planning agent to generate a codebase-aware implementation plan.

    This activity clones the repository, explores the codebase, generates
    a plan, and cleans up atomically within a single activity execution.

    Args:
        input: Planning parameters including issue and repository info.

    Returns:
        Activity output containing the plan and LLM execution metadata.
    """
    # Create adapters and planning service
    claude_client = ClaudeClient(model=config.claude.planning_model)
    repo_cloner = RepoCloner()
    planning_service = PlanningService(claude_client, repo_cloner)

    # Generate plan using input fields
    plan, llm_metadata_output = await planning_service.generate_plan(
        issue_title=input.issue_title,
        issue_body=input.issue_description,
        issue_number=input.issue_number,
        repo_owner=input.repo_owner,
        repo_name=input.repo_name,
        target_branch=input.target_branch,
    )

    # Convert Plan domain model to activity output structure
    plan_output = PlanOutput(
        summary=plan.summary,
        steps=[
            PlanStepOutput(
                id=step.id,
                description=step.description,
                completed=step.completed,
                related_files=step.related_files,
                estimated_complexity=step.estimated_complexity,
                substeps=[
                    TDDSubstepOutput(
                        id=substep.id,
                        phase=substep.phase,
                        description=substep.description,
                        file_operations=[
                            FileOperationOutput(
                                operation=file_op.operation,
                                file_path=file_op.file_path,
                                description=file_op.description,
                                line_range=file_op.line_range,
                                code_snippet=file_op.code_snippet,
                            )
                            for file_op in substep.file_operations
                        ],
                        verification=(
                            VerificationOutput(
                                command=substep.verification.command,
                                expected_outcome=substep.verification.expected_outcome,
                                expected_text=substep.verification.expected_text,
                                timeout_seconds=substep.verification.timeout_seconds,
                            )
                            if substep.verification
                            else None
                        ),
                        code_hints=substep.code_hints,
                        completed=substep.completed,
                        result=substep.result,
                    )
                    for substep in step.substeps
                ],
                commit_message_template=step.commit_message_template,
                depends_on=step.depends_on,
                preconditions=[
                    VerificationOutput(
                        command=precondition.command,
                        expected_outcome=precondition.expected_outcome,
                        expected_text=precondition.expected_text,
                        timeout_seconds=precondition.timeout_seconds,
                    )
                    for precondition in step.preconditions
                ],
            )
            for step in plan.steps
        ],
        created_at=plan.created_at,
        technical_approach=plan.technical_approach,
        testing_strategy=plan.testing_strategy,
        metadata=plan.metadata,
        based_on_commit=plan.based_on_commit,
    )

    return PlanningActivityOutput(plan=plan_output, llm_metadata=llm_metadata_output)

"""Planning-related Temporal activities.

Activities for AI-powered implementation planning.
"""

from pydantic import BaseModel, ConfigDict, Field
from temporalio import activity

from troller.config import config
from troller.worker.activities.activity_outputs import (
    LLMMetadataOutput,
    PlanOutput,
    PlanStepOutput,
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

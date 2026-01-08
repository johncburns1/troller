"""Implementation-related Temporal activities.

Activities for AI-powered code implementation.
"""

from pydantic import BaseModel, ConfigDict, Field
from temporalio import activity

from troller.config import config
from troller.domain.models.issue import Issue
from troller.domain.models.plan import Plan, PlanStep
from troller.worker.activities.activity_outputs import (
    CommitOutput,
    LLMMetadataOutput,
    PlanOutput,
)
from troller.worker.adapters.claude_client import ClaudeClient
from troller.worker.adapters.git_operations import GitOperations
from troller.worker.adapters.repo_cloner import RepoCloner
from troller.worker.services.implementation_service import ImplementationService


class ImplementationInput(BaseModel):
    """Input parameters for run_implementation_agent activity.

    Attributes:
        plan: Implementation plan to execute (as DTO).
        issue_number: GitHub issue number.
        issue_title: GitHub issue title.
        issue_description: GitHub issue description/body.
        issue_labels: List of label names.
        issue_url: Full URL to the issue.
        repo_owner: GitHub repository owner.
        repo_name: GitHub repository name.
        branch_name: Branch name to push changes to.
        target_branch: Base branch to clone from (defaults to main/master if None).
    """

    model_config = ConfigDict(frozen=True)

    plan: PlanOutput = Field(..., description="Implementation plan (DTO)")
    issue_number: int = Field(..., description="GitHub issue number", gt=0)
    issue_title: str = Field(..., description="GitHub issue title")
    issue_description: str = Field(..., description="GitHub issue description/body")
    issue_labels: list[str] = Field(
        default_factory=list, description="List of label names"
    )
    issue_url: str = Field(default="", description="Full URL to the issue")
    repo_owner: str = Field(..., description="GitHub repository owner")
    repo_name: str = Field(..., description="GitHub repository name")
    branch_name: str = Field(..., description="Branch name for commits")
    target_branch: str | None = Field(
        default=None, description="Base branch to clone (defaults to main/master)"
    )


class ImplementationActivityOutput(BaseModel):
    """Output from run_implementation_agent activity.

    Attributes:
        commits: List of commits created during implementation.
        llm_metadata: Metadata from LLM execution (cost, tokens, tools used, etc.).
    """

    model_config = ConfigDict(frozen=True)

    commits: list[CommitOutput] = Field(
        ..., description="Commits created during implementation"
    )
    llm_metadata: LLMMetadataOutput = Field(
        ..., description="LLM execution metadata for observability"
    )


@activity.defn
async def run_implementation_agent(
    input: ImplementationInput,
) -> ImplementationActivityOutput:
    """Run the implementation agent to execute code changes based on plan.

    This activity clones the repository, executes implementation using the
    feature-implementation skill, commits and pushes changes, and cleans up
    atomically within a single activity execution.

    Args:
        input: Implementation parameters including plan, issue, and repository info.

    Returns:
        Activity output containing commits and LLM execution metadata.
    """
    # Create adapters and implementation service
    claude_client = ClaudeClient(model=config.claude.coding_model)
    repo_cloner = RepoCloner()
    git_operations = GitOperations()
    implementation_service = ImplementationService(
        claude_client, repo_cloner, git_operations
    )

    # Convert PlanOutput DTO to Plan domain model
    plan = Plan(
        summary=input.plan.summary,
        steps=[
            PlanStep(
                id=step.id,
                description=step.description,
                completed=step.completed,
                related_files=step.related_files,
                estimated_complexity=step.estimated_complexity,
            )
            for step in input.plan.steps
        ],
        created_at=input.plan.created_at,
        technical_approach=input.plan.technical_approach,
        testing_strategy=input.plan.testing_strategy,
        metadata=input.plan.metadata,
        based_on_commit=input.plan.based_on_commit,
    )

    # Convert issue primitives to Issue domain model
    issue = Issue(
        number=input.issue_number,
        title=input.issue_title,
        description=input.issue_description,
        labels=input.issue_labels,
        url=input.issue_url,
    )

    # Execute implementation using domain models
    commits, llm_metadata_output = await implementation_service.implement_changes(
        plan=plan,
        issue=issue,
        repo_owner=input.repo_owner,
        repo_name=input.repo_name,
        branch_name=input.branch_name,
        target_branch=input.target_branch,
    )

    # Convert Commit domain models to activity output structure
    commit_outputs = [
        CommitOutput(
            sha=commit.sha,
            message=commit.message,
            timestamp=commit.timestamp,
            internal_review_feedback=None,  # No review feedback yet
        )
        for commit in commits
    ]

    return ImplementationActivityOutput(
        commits=commit_outputs, llm_metadata=llm_metadata_output
    )

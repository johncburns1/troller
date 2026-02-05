"""Review-related Temporal activities.

Activities for AI-powered code review and quality validation.
"""

from pydantic import BaseModel, ConfigDict, Field
from temporalio import activity

from troller.config import config
from troller.worker.activities.activity_outputs import (
    CommitOutput,
    InternalReviewFeedbackOutput,
    LLMMetadataOutput,
    PlanOutput,
)
from troller.worker.activities.converters import (
    commit_output_to_domain,
    issue_from_activity_input,
    plan_output_to_domain,
)
from troller.worker.adapters.claude_client import ClaudeClient
from troller.worker.adapters.repo_cloner import RepoCloner
from troller.worker.services.review_service import ReviewService


class ReviewInput(BaseModel):
    """Input parameters for run_review_agent activity.

    Attributes:
        commits: List of commits from implementation (as DTOs).
        plan: Implementation plan to verify against (as DTO).
        issue_number: GitHub issue number.
        issue_title: GitHub issue title.
        issue_description: GitHub issue description/body.
        issue_labels: List of label names.
        issue_url: Full URL to the issue.
        repo_owner: GitHub repository owner.
        repo_name: GitHub repository name.
        branch_name: Branch containing the implementation.
    """

    model_config = ConfigDict(frozen=True)

    commits: list[CommitOutput] = Field(..., description="Commits from implementation")
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
    branch_name: str = Field(..., description="Branch containing implementation")


class ReviewActivityOutput(BaseModel):
    """Output from run_review_agent activity.

    Attributes:
        feedback: Review feedback from the Review Agent.
        llm_metadata: Metadata from LLM execution (cost, tokens, etc.).
    """

    model_config = ConfigDict(frozen=True)

    feedback: InternalReviewFeedbackOutput = Field(
        ..., description="Review feedback from the agent"
    )
    llm_metadata: LLMMetadataOutput = Field(
        ..., description="LLM execution metadata for observability"
    )


@activity.defn
async def run_review_agent(input: ReviewInput) -> ReviewActivityOutput:
    """Run the review agent to evaluate code quality and plan adherence.

    This activity clones the repository, uses Claude structured query to
    evaluate the implementation against the plan, and returns feedback.

    Args:
        input: Review parameters including commits, plan, issue, and repository info.

    Returns:
        Activity output containing review feedback and LLM execution metadata.
    """
    # Create adapters and review service
    claude_client = ClaudeClient(model=config.claude.review_model)
    repo_cloner = RepoCloner()
    review_service = ReviewService(
        claude_client=claude_client,
        repo_cloner=repo_cloner,
        model=config.claude.review_model,
    )

    # Convert DTOs to domain models using shared converters
    commits = [commit_output_to_domain(commit) for commit in input.commits]
    plan = plan_output_to_domain(input.plan)
    issue = issue_from_activity_input(
        number=input.issue_number,
        title=input.issue_title,
        description=input.issue_description,
        labels=input.issue_labels,
        url=input.issue_url,
    )

    # Execute review using domain models
    feedback, llm_metadata = await review_service.review_changes(
        commits=commits,
        plan=plan,
        issue=issue,
        repo_owner=input.repo_owner,
        repo_name=input.repo_name,
        branch_name=input.branch_name,
    )

    # Convert InternalReviewFeedback domain model to activity output structure
    feedback_output = InternalReviewFeedbackOutput(
        approved=feedback.approved,
        comments=feedback.comments,
        suggested_changes=feedback.suggested_changes,
        timestamp=feedback.timestamp,
    )

    return ReviewActivityOutput(feedback=feedback_output, llm_metadata=llm_metadata)

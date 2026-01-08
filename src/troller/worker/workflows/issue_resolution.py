"""Issue resolution Temporal workflow.

Orchestrates the planning process for GitHub issue resolution.
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from troller.domain.models.issue import Issue
    from troller.worker.activities.github_activities import (
        FetchIssueInput,
        FetchIssueOutput,
        fetch_issue,
    )
    from troller.worker.activities.planning_activities import (
        PlanningInput,
        run_planning_agent,
    )
    from troller.worker.workflows.data_structures import (
        IssueResolutionWorkflowInput,
        IssueResolutionWorkflowOutput,
    )


@workflow.defn
class IssueResolutionWorkflow:
    """Workflow that orchestrates issue resolution planning.

    This workflow fetches a GitHub issue, runs the planning agent to generate
    an implementation plan, and stores the plan in workflow state.
    """

    def __init__(self) -> None:
        """Initialize workflow state."""
        self._issue: Issue | None = None

    @workflow.run
    async def run(
        self, input: IssueResolutionWorkflowInput
    ) -> IssueResolutionWorkflowOutput:
        """Execute the issue resolution workflow.

        Args:
            input: Workflow input parameters.

        Returns:
            Workflow output containing the implementation plan.

        Raises:
            ActivityError: If any activity fails.
        """
        # Fetch issue from GitHub
        issue_output: FetchIssueOutput = await workflow.execute_activity(
            fetch_issue,
            FetchIssueInput(
                repo_owner=input.repo_owner,
                repo_name=input.repo_name,
                issue_number=input.issue_number,
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
            ),
        )

        # Convert activity output to domain model (domain models live in workflow)
        self._issue = Issue(
            number=issue_output.number,
            title=issue_output.title,
            description=issue_output.description,
            labels=issue_output.labels,
            url=issue_output.url,
        )

        # Run planning agent (may take a few minutes due to repo cloning and exploration)
        # Pass issue data as individual fields
        planning_output = await workflow.execute_activity(
            run_planning_agent,
            PlanningInput(
                issue_number=self._issue.number,
                issue_title=self._issue.title,
                issue_description=self._issue.description,
                issue_labels=self._issue.labels,
                issue_url=self._issue.url,
                repo_owner=input.repo_owner,
                repo_name=input.repo_name,
                target_branch=input.target_branch,
            ),
            start_to_close_timeout=timedelta(
                minutes=10
            ),  # Increased for cloning + exploration
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(seconds=30),
            ),
        )

        # Return workflow output with plan DTO
        return IssueResolutionWorkflowOutput(plan=planning_output.plan)

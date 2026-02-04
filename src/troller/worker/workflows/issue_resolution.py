"""Issue resolution Temporal workflow.

Orchestrates the planning process for GitHub issue resolution.
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from troller.domain.models.issue import Issue
    from troller.worker.activities.activity_outputs import (
        CommitOutput,
        InternalReviewFeedbackOutput,
    )
    from troller.worker.activities.github_activities import (
        CreateFeatureBranchInput,
        CreatePullRequestInput,
        CreatePullRequestOutput,
        FetchIssueInput,
        FetchIssueOutput,
        create_feature_branch,
        create_pull_request,
        fetch_issue,
    )
    from troller.worker.activities.implementation_activities import (
        ImplementationActivityOutput,
        ImplementationInput,
        run_implementation_agent,
    )
    from troller.worker.activities.planning_activities import (
        PlanningInput,
        run_planning_agent,
    )
    from troller.worker.activities.review_activities import (
        ReviewActivityOutput,
        ReviewInput,
        run_review_agent,
    )
    from troller.worker.workflows.data_structures import (
        IssueResolutionWorkflowInput,
        IssueResolutionWorkflowOutput,
    )


@workflow.defn
class IssueResolutionWorkflow:
    """Workflow that orchestrates full issue resolution.

    This workflow orchestrates the complete autonomous issue resolution flow:
    1. Fetches GitHub issue
    2. Creates feature branch
    3. Generates implementation plan
    4. Implements changes via coding agent
    5. Reviews implementation (max 1 round)
    6. Creates pull request
    """

    # Maximum number of review rounds to prevent infinite loops
    MAX_REVIEW_ROUNDS = 1

    def __init__(self) -> None:
        """Initialize workflow state."""
        self._issue: Issue | None = None
        self._branch_name: str | None = None
        self._commits: list[CommitOutput] = []
        self._pull_request: CreatePullRequestOutput | None = None
        self._review_feedback: InternalReviewFeedbackOutput | None = None

    @workflow.run
    async def run(
        self, input: IssueResolutionWorkflowInput
    ) -> IssueResolutionWorkflowOutput:
        """Execute the issue resolution workflow.

        Args:
            input: Workflow input parameters.

        Returns:
            Workflow output containing plan, branch, commits, and pull request.

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

        # Create feature branch first
        self._branch_name = f"troller/issue-{self._issue.number}"
        await workflow.execute_activity(
            create_feature_branch,
            CreateFeatureBranchInput(
                repo_owner=input.repo_owner,
                repo_name=input.repo_name,
                branch_name=self._branch_name,
                base_branch=input.target_branch or "main",
            ),
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
            ),
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

        # Run implementation agent (self-contained: clones, implements, commits, pushes)
        impl_output: ImplementationActivityOutput = await workflow.execute_activity(
            run_implementation_agent,
            ImplementationInput(
                plan=planning_output.plan,
                issue_number=self._issue.number,
                issue_title=self._issue.title,
                issue_description=self._issue.description,
                issue_labels=self._issue.labels,
                issue_url=self._issue.url,
                repo_owner=input.repo_owner,
                repo_name=input.repo_name,
                branch_name=self._branch_name,
                target_branch=input.target_branch,
            ),
            start_to_close_timeout=timedelta(minutes=20),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(seconds=30),
            ),
        )
        self._commits.extend(impl_output.commits)

        # Run review agent to evaluate implementation
        review_output: ReviewActivityOutput = await workflow.execute_activity(
            run_review_agent,
            ReviewInput(
                commits=self._commits,
                plan=planning_output.plan,
                issue_number=self._issue.number,
                issue_title=self._issue.title,
                issue_description=self._issue.description,
                issue_labels=self._issue.labels,
                issue_url=self._issue.url,
                repo_owner=input.repo_owner,
                repo_name=input.repo_name,
                branch_name=self._branch_name,
            ),
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(seconds=30),
            ),
        )
        self._review_feedback = review_output.feedback

        # If review rejected and we haven't exceeded max review rounds,
        # run implementation again with feedback
        review_round = 0
        while (
            not self._review_feedback.approved and review_round < self.MAX_REVIEW_ROUNDS
        ):
            review_round += 1

            # Build feedback message for implementation agent
            feedback_message = self._build_feedback_message(self._review_feedback)

            # Re-run implementation with review feedback
            impl_output = await workflow.execute_activity(
                run_implementation_agent,
                ImplementationInput(
                    plan=planning_output.plan,
                    issue_number=self._issue.number,
                    issue_title=self._issue.title,
                    issue_description=f"{self._issue.description}\n\n{feedback_message}",
                    issue_labels=self._issue.labels,
                    issue_url=self._issue.url,
                    repo_owner=input.repo_owner,
                    repo_name=input.repo_name,
                    branch_name=self._branch_name,
                    target_branch=input.target_branch,
                ),
                start_to_close_timeout=timedelta(minutes=20),
                retry_policy=RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(seconds=5),
                    maximum_interval=timedelta(seconds=30),
                ),
            )
            self._commits.extend(impl_output.commits)

            # Re-run review
            review_output = await workflow.execute_activity(
                run_review_agent,
                ReviewInput(
                    commits=self._commits,
                    plan=planning_output.plan,
                    issue_number=self._issue.number,
                    issue_title=self._issue.title,
                    issue_description=self._issue.description,
                    issue_labels=self._issue.labels,
                    issue_url=self._issue.url,
                    repo_owner=input.repo_owner,
                    repo_name=input.repo_name,
                    branch_name=self._branch_name,
                ),
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(seconds=5),
                    maximum_interval=timedelta(seconds=30),
                ),
            )
            self._review_feedback = review_output.feedback

        # Create PR after implementation and review is complete
        pr_body = f"""Resolves #{self._issue.number}

## Description
{self._issue.description}

This PR implements the changes needed to resolve this issue using autonomous AI agents.

🤖 Generated by Troller
"""
        self._pull_request = await workflow.execute_activity(
            create_pull_request,
            CreatePullRequestInput(
                repo_owner=input.repo_owner,
                repo_name=input.repo_name,
                title=f"Fix #{self._issue.number}: {self._issue.title}",
                body=pr_body,
                head_branch=self._branch_name,
                base_branch=input.target_branch or "main",
                draft=False,  # Implementation is complete
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
            ),
        )

        # Return workflow output with complete result
        return IssueResolutionWorkflowOutput(
            plan=planning_output.plan,
            branch_name=self._branch_name,
            commits=self._commits,
            pull_request=self._pull_request,
        )

    def _build_feedback_message(self, feedback: InternalReviewFeedbackOutput) -> str:
        """Build feedback message for implementation agent from review feedback.

        Args:
            feedback: Review feedback containing comments and suggested changes.

        Returns:
            Formatted feedback message for the implementation agent.
        """
        lines = ["## Review Feedback (Please address these items)"]

        if feedback.comments:
            lines.append("\n### Review Comments:")
            for comment in feedback.comments:
                lines.append(f"- {comment}")

        if feedback.suggested_changes:
            lines.append("\n### Required Changes:")
            for change in feedback.suggested_changes:
                lines.append(f"- {change}")

        return "\n".join(lines)

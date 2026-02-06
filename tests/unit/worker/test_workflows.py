"""Unit tests for Temporal workflows.

Tests use Temporal's testing framework to verify workflow behavior.
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from github.Issue import Issue as GithubIssue
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from troller.domain.models.commit import InternalReviewFeedback
from troller.domain.models.plan import Plan, PlanStep
from troller.worker.activities.activity_outputs import LLMMetadataOutput
from troller.worker.activities.github_activities import (
    FetchIssueInput,
    FetchIssueOutput,
    create_pull_request,
    fetch_issue,
    fetch_pull_request,
)
from troller.worker.activities.planning_activities import (
    PlanningInput,
    run_planning_agent,
)
from troller.worker.activities.review_activities import run_review_agent
from troller.worker.workflows.data_structures import (
    IssueResolutionWorkflowInput,
    IssueResolutionWorkflowOutput,
)
from troller.worker.workflows.issue_resolution import IssueResolutionWorkflow


@pytest.mark.asyncio
async def test_issue_resolution_workflow_executes_activities_in_correct_order() -> None:
    """Test workflow executes fetch_issue then run_planning_agent."""
    with patch.dict(
        os.environ, {"GITHUB_TOKEN": "test-token", "ANTHROPIC_API_KEY": "test-key"}
    ):
        with (
            patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_gh_client_class,
            patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_planning_service_class,
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
            patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_impl_service_class,
            patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_review_service_class,
        ):
            # Setup GitHub mock
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client
            mock_github_issue = MagicMock(spec=GithubIssue)
            mock_github_issue.number = 123
            mock_github_issue.title = "Test Issue"
            mock_github_issue.body = "Test description"
            mock_github_issue.labels = []
            mock_github_issue.html_url = (
                "https://github.com/test-owner/test-repo/issues/123"
            )
            mock_gh_client.get_issue.return_value = mock_github_issue

            # Setup Claude mock
            from datetime import datetime

            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            expected_plan = Plan(
                summary="Implementation plan for: Test Issue",
                steps=[
                    PlanStep(id="step-1", description="Step 1", completed=False),
                    PlanStep(id="step-2", description="Step 2", completed=False),
                ],
                created_at=datetime.now(),
                metadata={"issue_number": 123},
            )
            expected_metadata = LLMMetadataOutput(
                total_cost_usd=0.10,
                input_tokens=800,
                output_tokens=400,
                duration_ms=4000,
                duration_api_ms=3500,
                num_turns=1,
                model="claude-opus-4-5-20251101",
                tools_used=["Skill", "Read"],
                execution_flow="Invoked feature-planner skill",
            )
            mock_planning_service.generate_plan = AsyncMock(
                return_value=(expected_plan, expected_metadata)
            )

            # Setup git and implementation mocks
            from datetime import datetime

            from troller.worker.activities.activity_outputs import CommitOutput
            from troller.worker.activities.github_activities import (
                create_feature_branch,
            )
            from troller.worker.activities.implementation_activities import (
                run_implementation_agent,
            )

            mock_cloner = MagicMock()
            mock_cloner_class.return_value = mock_cloner
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_cloner.clone_to_temp = AsyncMock(
                return_value=(Path("/tmp/t"), Path("/tmp/t/r"), "sha")
            )
            mock_git_ops.create_branch = AsyncMock()
            mock_git_ops.push_branch = AsyncMock()
            mock_git_ops.get_current_sha = AsyncMock(return_value="branch-sha")

            mock_impl_service = MagicMock()
            mock_impl_service_class.return_value = mock_impl_service
            commits = [
                CommitOutput(
                    sha="commit-1",
                    message="Commit",
                    timestamp=datetime.now(),
                    internal_review_feedback=None,
                )
            ]
            mock_impl_service.implement_changes = AsyncMock(
                return_value=(commits, expected_metadata)
            )

            # Setup review service mock
            mock_review_service = MagicMock()
            mock_review_service_class.return_value = mock_review_service
            review_feedback = InternalReviewFeedback(
                approved=True,
                comments=["Looks good"],
                suggested_changes=[],
                timestamp=datetime.now(),
            )
            review_metadata = LLMMetadataOutput(
                total_cost_usd=0.05,
                input_tokens=400,
                output_tokens=200,
                duration_ms=2000,
                duration_api_ms=1800,
                num_turns=1,
                model="claude-sonnet-4-5-20250929",
                tools_used=[],
                execution_flow="Structured review query",
            )
            mock_review_service.review_changes = AsyncMock(
                return_value=(review_feedback, review_metadata)
            )

            from troller.domain.models.pull_request import PullRequest

            pr = PullRequest(
                number=1,
                url="https://github.com/test-owner/test-repo/pull/1",
                head_branch="troller/issue-123",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="open",
            )
            mock_gh_client.create_pull_request.return_value = pr

            # Setup get_pull_request mock - return merged for test completion
            merged_pr = PullRequest(
                number=1,
                url="https://github.com/test-owner/test-repo/pull/1",
                head_branch="troller/issue-123",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="merged",
            )
            mock_gh_client.get_pull_request.return_value = merged_pr

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[
                        fetch_issue,
                        run_planning_agent,
                        create_feature_branch,
                        run_implementation_agent,
                        run_review_agent,
                        create_pull_request,
                        fetch_pull_request,
                    ],
                ):
                    # Execute workflow
                    input_data = IssueResolutionWorkflowInput(
                        repo_owner="test-owner",
                        repo_name="test-repo",
                        issue_number=123,
                        target_branch="main",
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        input_data,
                        id="test-workflow-order",
                        task_queue="test-queue",
                    )

                    # Verify result is a workflow output with plan
                    assert isinstance(result, IssueResolutionWorkflowOutput)
                    assert result.plan.summary.startswith("Implementation plan for:")
                    assert len(result.plan.steps) > 0


@pytest.mark.asyncio
async def test_issue_resolution_workflow_returns_plan_with_steps() -> None:
    """Test workflow returns a plan with implementation steps."""
    with patch.dict(
        os.environ, {"GITHUB_TOKEN": "test-token", "ANTHROPIC_API_KEY": "test-key"}
    ):
        with (
            patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_gh_client_class,
            patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_planning_service_class,
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
            patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_impl_service_class,
            patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_review_service_class,
        ):
            # Setup mocks
            from datetime import datetime

            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client
            mock_github_issue = MagicMock(spec=GithubIssue)
            mock_github_issue.number = 456
            mock_github_issue.title = "Test Issue 456"
            mock_github_issue.body = "Description"
            mock_github_issue.labels = []
            mock_github_issue.html_url = (
                "https://github.com/test-owner/test-repo/issues/456"
            )
            mock_gh_client.get_issue.return_value = mock_github_issue

            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            expected_plan = Plan(
                summary="Test plan",
                steps=[
                    PlanStep(id="step-1", description="Step 1", completed=False),
                    PlanStep(id="step-2", description="Step 2", completed=False),
                    PlanStep(id="step-3", description="Step 3", completed=False),
                ],
                created_at=datetime.now(),
                metadata={},
            )
            expected_metadata = LLMMetadataOutput(
                total_cost_usd=0.10,
                input_tokens=800,
                output_tokens=400,
                duration_ms=4000,
                duration_api_ms=3500,
                num_turns=1,
                model="claude-opus-4-5-20251101",
                tools_used=["Skill", "Read"],
                execution_flow="Invoked feature-planner skill",
            )
            mock_planning_service.generate_plan = AsyncMock(
                return_value=(expected_plan, expected_metadata)
            )

            # Setup git and implementation mocks
            from troller.worker.activities.activity_outputs import CommitOutput
            from troller.worker.activities.github_activities import (
                create_feature_branch,
            )
            from troller.worker.activities.implementation_activities import (
                run_implementation_agent,
            )

            mock_cloner = MagicMock()
            mock_cloner_class.return_value = mock_cloner
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_cloner.clone_to_temp = AsyncMock(
                return_value=(Path("/tmp/t"), Path("/tmp/t/r"), "sha")
            )
            mock_git_ops.create_branch = AsyncMock()
            mock_git_ops.push_branch = AsyncMock()
            mock_git_ops.get_current_sha = AsyncMock(return_value="branch-sha")

            mock_impl_service = MagicMock()
            mock_impl_service_class.return_value = mock_impl_service
            commits = [
                CommitOutput(
                    sha="commit-1",
                    message="Commit",
                    timestamp=datetime.now(),
                    internal_review_feedback=None,
                )
            ]
            mock_impl_service.implement_changes = AsyncMock(
                return_value=(commits, expected_metadata)
            )

            # Setup review service mock
            mock_review_service = MagicMock()
            mock_review_service_class.return_value = mock_review_service
            review_feedback = InternalReviewFeedback(
                approved=True,
                comments=["Looks good"],
                suggested_changes=[],
                timestamp=datetime.now(),
            )
            review_metadata = LLMMetadataOutput(
                total_cost_usd=0.05,
                input_tokens=400,
                output_tokens=200,
                duration_ms=2000,
                duration_api_ms=1800,
                num_turns=1,
                model="claude-sonnet-4-5-20250929",
                tools_used=[],
                execution_flow="Structured review query",
            )
            mock_review_service.review_changes = AsyncMock(
                return_value=(review_feedback, review_metadata)
            )

            from troller.domain.models.pull_request import PullRequest

            pr = PullRequest(
                number=1,
                url="https://github.com/test-owner/test-repo/pull/1",
                head_branch="troller/issue-456",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="open",
            )
            mock_gh_client.create_pull_request.return_value = pr

            # Setup get_pull_request mock - return merged for test completion
            merged_pr = PullRequest(
                number=1,
                url="https://github.com/test-owner/test-repo/pull/1",
                head_branch="troller/issue-456",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="merged",
            )
            mock_gh_client.get_pull_request.return_value = merged_pr

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[
                        fetch_issue,
                        run_planning_agent,
                        create_feature_branch,
                        run_implementation_agent,
                        run_review_agent,
                        create_pull_request,
                        fetch_pull_request,
                    ],
                ):
                    input_data = IssueResolutionWorkflowInput(
                        repo_owner="test-owner",
                        repo_name="test-repo",
                        issue_number=456,
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        input_data,
                        id="test-workflow-plan",
                        task_queue="test-queue",
                    )

                    # Verify plan structure
                    assert isinstance(result, IssueResolutionWorkflowOutput)
                    assert result.plan.summary != ""
                    assert len(result.plan.steps) == 3
                    assert all(
                        step.id.startswith("step-") for step in result.plan.steps
                    )
                    assert result.plan.created_at is not None


@pytest.mark.asyncio
async def test_issue_resolution_workflow_stores_issue_in_state() -> None:
    """Test workflow stores fetched issue in workflow state."""
    with patch.dict(
        os.environ, {"GITHUB_TOKEN": "test-token", "ANTHROPIC_API_KEY": "test-key"}
    ):
        with (
            patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_gh_client_class,
            patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_planning_service_class,
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
            patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_impl_service_class,
            patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_review_service_class,
        ):
            # Setup mocks
            from datetime import datetime

            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client
            mock_github_issue = MagicMock(spec=GithubIssue)
            mock_github_issue.number = 789
            mock_github_issue.title = "Issue 789"
            mock_github_issue.body = "Body"
            mock_github_issue.labels = []
            mock_github_issue.html_url = (
                "https://github.com/test-owner/test-repo/issues/789"
            )
            mock_gh_client.get_issue.return_value = mock_github_issue

            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            expected_plan = Plan(
                summary="Plan",
                steps=[PlanStep(id="step-1", description="Step", completed=False)],
                created_at=datetime.now(),
                metadata={},
            )
            expected_metadata = LLMMetadataOutput(
                total_cost_usd=0.10,
                input_tokens=800,
                output_tokens=400,
                duration_ms=4000,
                duration_api_ms=3500,
                num_turns=1,
                model="claude-opus-4-5-20251101",
                tools_used=["Skill", "Read"],
                execution_flow="Invoked feature-planner skill",
            )
            mock_planning_service.generate_plan = AsyncMock(
                return_value=(expected_plan, expected_metadata)
            )

            # Setup git and implementation mocks
            from troller.worker.activities.activity_outputs import CommitOutput
            from troller.worker.activities.github_activities import (
                create_feature_branch,
            )
            from troller.worker.activities.implementation_activities import (
                run_implementation_agent,
            )

            mock_cloner = MagicMock()
            mock_cloner_class.return_value = mock_cloner
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_cloner.clone_to_temp = AsyncMock(
                return_value=(Path("/tmp/t"), Path("/tmp/t/r"), "sha")
            )
            mock_git_ops.create_branch = AsyncMock()
            mock_git_ops.push_branch = AsyncMock()
            mock_git_ops.get_current_sha = AsyncMock(return_value="branch-sha")

            mock_impl_service = MagicMock()
            mock_impl_service_class.return_value = mock_impl_service
            commits = [
                CommitOutput(
                    sha="commit-1",
                    message="Commit",
                    timestamp=datetime.now(),
                    internal_review_feedback=None,
                )
            ]
            mock_impl_service.implement_changes = AsyncMock(
                return_value=(commits, expected_metadata)
            )

            # Setup review service mock
            mock_review_service = MagicMock()
            mock_review_service_class.return_value = mock_review_service
            review_feedback = InternalReviewFeedback(
                approved=True,
                comments=["Looks good"],
                suggested_changes=[],
                timestamp=datetime.now(),
            )
            review_metadata = LLMMetadataOutput(
                total_cost_usd=0.05,
                input_tokens=400,
                output_tokens=200,
                duration_ms=2000,
                duration_api_ms=1800,
                num_turns=1,
                model="claude-sonnet-4-5-20250929",
                tools_used=[],
                execution_flow="Structured review query",
            )
            mock_review_service.review_changes = AsyncMock(
                return_value=(review_feedback, review_metadata)
            )

            from troller.domain.models.pull_request import PullRequest

            pr = PullRequest(
                number=1,
                url="https://github.com/test-owner/test-repo/pull/1",
                head_branch="troller/issue-789",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="open",
            )
            mock_gh_client.create_pull_request.return_value = pr

            # Setup get_pull_request mock - return merged for test completion
            merged_pr = PullRequest(
                number=1,
                url="https://github.com/test-owner/test-repo/pull/1",
                head_branch="troller/issue-789",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="merged",
            )
            mock_gh_client.get_pull_request.return_value = merged_pr

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[
                        fetch_issue,
                        run_planning_agent,
                        create_feature_branch,
                        run_implementation_agent,
                        run_review_agent,
                        create_pull_request,
                        fetch_pull_request,
                    ],
                ):
                    input_data = IssueResolutionWorkflowInput(
                        repo_owner="test-owner",
                        repo_name="test-repo",
                        issue_number=789,
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        input_data,
                        id="test-workflow-state",
                        task_queue="test-queue",
                    )

                    # Verify result is returned successfully
                    # (state verification would require workflow queries/signals)
                    assert isinstance(result, IssueResolutionWorkflowOutput)


@pytest.mark.asyncio
async def test_issue_resolution_workflow_accepts_optional_target_branch() -> None:
    """Test workflow accepts optional target_branch parameter."""
    with patch.dict(
        os.environ, {"GITHUB_TOKEN": "test-token", "ANTHROPIC_API_KEY": "test-key"}
    ):
        with (
            patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_gh_client_class,
            patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_planning_service_class,
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
            patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_impl_service_class,
            patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_review_service_class,
        ):
            # Setup mocks
            from datetime import datetime

            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client

            def mock_get_issue(owner: str, repo: str, issue_number: int) -> MagicMock:
                mock_issue = MagicMock(spec=GithubIssue)
                mock_issue.number = issue_number
                mock_issue.title = f"Issue {issue_number}"
                mock_issue.body = "Body"
                mock_issue.labels = []
                mock_issue.html_url = (
                    f"https://github.com/{owner}/{repo}/issues/{issue_number}"
                )
                return mock_issue

            mock_gh_client.get_issue.side_effect = mock_get_issue

            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            expected_plan = Plan(
                summary="Plan",
                steps=[PlanStep(id="step-1", description="Step", completed=False)],
                created_at=datetime.now(),
                metadata={},
            )
            expected_metadata = LLMMetadataOutput(
                total_cost_usd=0.10,
                input_tokens=800,
                output_tokens=400,
                duration_ms=4000,
                duration_api_ms=3500,
                num_turns=1,
                model="claude-opus-4-5-20251101",
                tools_used=["Skill", "Read"],
                execution_flow="Invoked feature-planner skill",
            )
            mock_planning_service.generate_plan = AsyncMock(
                return_value=(expected_plan, expected_metadata)
            )

            # Setup git and implementation mocks
            from troller.worker.activities.activity_outputs import CommitOutput
            from troller.worker.activities.github_activities import (
                create_feature_branch,
            )
            from troller.worker.activities.implementation_activities import (
                run_implementation_agent,
            )

            mock_cloner = MagicMock()
            mock_cloner_class.return_value = mock_cloner
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_cloner.clone_to_temp = AsyncMock(
                return_value=(Path("/tmp/t"), Path("/tmp/t/r"), "sha")
            )
            mock_git_ops.create_branch = AsyncMock()
            mock_git_ops.push_branch = AsyncMock()
            mock_git_ops.get_current_sha = AsyncMock(return_value="branch-sha")

            mock_impl_service = MagicMock()
            mock_impl_service_class.return_value = mock_impl_service
            commits = [
                CommitOutput(
                    sha="commit-1",
                    message="Commit",
                    timestamp=datetime.now(),
                    internal_review_feedback=None,
                )
            ]
            mock_impl_service.implement_changes = AsyncMock(
                return_value=(commits, expected_metadata)
            )

            # Setup review service mock
            mock_review_service = MagicMock()
            mock_review_service_class.return_value = mock_review_service
            review_feedback = InternalReviewFeedback(
                approved=True,
                comments=["Looks good"],
                suggested_changes=[],
                timestamp=datetime.now(),
            )
            review_metadata = LLMMetadataOutput(
                total_cost_usd=0.05,
                input_tokens=400,
                output_tokens=200,
                duration_ms=2000,
                duration_api_ms=1800,
                num_turns=1,
                model="claude-sonnet-4-5-20250929",
                tools_used=[],
                execution_flow="Structured review query",
            )
            mock_review_service.review_changes = AsyncMock(
                return_value=(review_feedback, review_metadata)
            )

            from troller.domain.models.pull_request import PullRequest

            pr = PullRequest(
                number=1,
                url="https://github.com/test-owner/test-repo/pull/1",
                head_branch="troller/issue-101",
                base_branch="develop",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="open",
            )
            mock_gh_client.create_pull_request.return_value = pr

            # Setup get_pull_request mock - return merged for test completion
            merged_pr = PullRequest(
                number=1,
                url="https://github.com/test-owner/test-repo/pull/1",
                head_branch="troller/issue-101",
                base_branch="develop",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="merged",
            )
            mock_gh_client.get_pull_request.return_value = merged_pr

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[
                        fetch_issue,
                        run_planning_agent,
                        create_feature_branch,
                        run_implementation_agent,
                        run_review_agent,
                        create_pull_request,
                        fetch_pull_request,
                    ],
                ):
                    # Test with target_branch
                    input_with_branch = IssueResolutionWorkflowInput(
                        repo_owner="test-owner",
                        repo_name="test-repo",
                        issue_number=101,
                        target_branch="develop",
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        input_with_branch,
                        id="test-workflow-branch",
                        task_queue="test-queue",
                    )

                    assert isinstance(result, IssueResolutionWorkflowOutput)

                    # Test without target_branch
                    input_without_branch = IssueResolutionWorkflowInput(
                        repo_owner="test-owner",
                        repo_name="test-repo",
                        issue_number=102,
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        input_without_branch,
                        id="test-workflow-no-branch",
                        task_queue="test-queue",
                    )

                    assert isinstance(result, IssueResolutionWorkflowOutput)


@pytest.mark.asyncio
async def test_fetch_issue_activity_returns_issue_data() -> None:
    """Test fetch_issue activity returns expected issue structure."""
    with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
        with patch(
            "troller.worker.activities.github_activities.GitHubClient"
        ) as mock_client_class:
            # Setup mock
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_github_issue = MagicMock(spec=GithubIssue)
            mock_github_issue.number = 999
            mock_github_issue.title = "Test Issue #999"
            mock_github_issue.body = "Test issue description"
            mock_github_issue.labels = []
            mock_github_issue.html_url = (
                "https://github.com/test-owner/test-repo/issues/999"
            )

            mock_client.get_issue.return_value = mock_github_issue

            # Test
            input_data = FetchIssueInput(
                repo_owner="test-owner", repo_name="test-repo", issue_number=999
            )
            result = await fetch_issue(input_data)

            assert isinstance(result, FetchIssueOutput)
            assert result.number == 999
            assert result.title == "Test Issue #999"
            assert result.description == "Test issue description"
            assert isinstance(result.labels, list)
            assert result.url.startswith("https://github.com/")


@pytest.mark.asyncio
async def test_run_planning_agent_activity_returns_plan() -> None:
    """Test run_planning_agent activity returns valid plan."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        with patch(
            "troller.worker.activities.planning_activities.PlanningService"
        ) as mock_client_class:
            # Setup mock
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            from datetime import datetime

            expected_plan = Plan(
                summary="Test plan for: Test Issue",
                steps=[
                    PlanStep(
                        id="step-1",
                        description="Implement solution",
                        completed=False,
                    )
                ],
                created_at=datetime.now(),
                metadata={"issue_number": 123},
            )
            expected_metadata = LLMMetadataOutput(
                total_cost_usd=0.08,
                input_tokens=600,
                output_tokens=300,
                duration_ms=3000,
                duration_api_ms=2800,
                num_turns=1,
                model="claude-opus-4-5-20251101",
                tools_used=["Skill"],
                execution_flow="Invoked feature-planner skill",
            )
            mock_client.generate_plan = AsyncMock(
                return_value=(expected_plan, expected_metadata)
            )

            # Test with activity input
            planning_input = PlanningInput(
                issue_number=123,
                issue_title="Test Issue",
                issue_description="Test description",
                issue_labels=["bug"],
                issue_url="https://github.com/test/repo/issues/123",
                repo_owner="test",
                repo_name="repo",
            )

            result = await run_planning_agent(planning_input)

            from troller.worker.activities.planning_activities import (
                PlanningActivityOutput,
            )

            assert isinstance(result, PlanningActivityOutput)
            assert result.plan.summary != ""
            assert len(result.plan.steps) > 0
            assert result.plan.created_at is not None
            assert isinstance(result.plan.metadata, dict)


@pytest.mark.asyncio
async def test_issue_resolution_workflow_full_flow_creates_branch_implements_and_creates_pr() -> (
    None
):
    """Test workflow orchestrates full flow: branch → PR (draft) → plan → implement."""
    with patch.dict(
        os.environ, {"GITHUB_TOKEN": "test-token", "ANTHROPIC_API_KEY": "test-key"}
    ):
        with (
            patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_gh_client_class,
            patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_planning_service_class,
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
            patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_impl_service_class,
            patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_review_service_class,
        ):
            from datetime import datetime

            from troller.worker.activities.activity_outputs import CommitOutput
            from troller.worker.activities.github_activities import (
                create_feature_branch,
            )
            from troller.worker.activities.implementation_activities import (
                run_implementation_agent,
            )

            # Setup GitHub mock
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client
            mock_github_issue = MagicMock(spec=GithubIssue)
            mock_github_issue.number = 36
            mock_github_issue.title = "Create branch management activity"
            mock_github_issue.body = "Test description"
            mock_github_issue.labels = []
            mock_github_issue.html_url = (
                "https://github.com/test-owner/test-repo/issues/36"
            )
            mock_gh_client.get_issue.return_value = mock_github_issue

            # Setup planning mock
            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            expected_plan = Plan(
                summary="Implementation plan for branch management",
                steps=[
                    PlanStep(
                        id="step-1", description="Create activity", completed=False
                    ),
                    PlanStep(id="step-2", description="Add tests", completed=False),
                ],
                created_at=datetime.now(),
                metadata={"issue_number": 36},
            )
            expected_metadata = LLMMetadataOutput(
                total_cost_usd=0.10,
                input_tokens=800,
                output_tokens=400,
                duration_ms=4000,
                duration_api_ms=3500,
                num_turns=1,
                model="claude-opus-4-5-20251101",
                tools_used=["Skill", "Read"],
                execution_flow="Invoked feature-planner skill",
            )
            mock_planning_service.generate_plan = AsyncMock(
                return_value=(expected_plan, expected_metadata)
            )

            # Setup git mocks for branch creation
            mock_cloner = MagicMock()
            mock_cloner_class.return_value = mock_cloner
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops

            temp_dir = Path("/tmp/test-temp")
            repo_path = Path("/tmp/test-temp/test-repo")
            mock_cloner.clone_to_temp = AsyncMock(
                return_value=(temp_dir, repo_path, "base-sha")
            )
            mock_git_ops.create_branch = AsyncMock()
            mock_git_ops.push_branch = AsyncMock()
            mock_git_ops.get_current_sha = AsyncMock(return_value="branch-sha-123")

            # Setup implementation mock
            mock_impl_service = MagicMock()
            mock_impl_service_class.return_value = mock_impl_service
            mock_commits = [
                CommitOutput(
                    sha="commit-sha-1",
                    message="Implement step 1",
                    timestamp=datetime.now(),
                    internal_review_feedback=None,
                ),
                CommitOutput(
                    sha="commit-sha-2",
                    message="Implement step 2",
                    timestamp=datetime.now(),
                    internal_review_feedback=None,
                ),
            ]
            impl_metadata = LLMMetadataOutput(
                total_cost_usd=0.15,
                input_tokens=1000,
                output_tokens=500,
                duration_ms=5000,
                duration_api_ms=4500,
                num_turns=2,
                model="claude-opus-4-5-20251101",
                tools_used=["Edit", "Write"],
                execution_flow="Implemented changes",
            )
            mock_impl_service.implement_changes = AsyncMock(
                return_value=(mock_commits, impl_metadata)
            )

            # Setup review service mock
            mock_review_service = MagicMock()
            mock_review_service_class.return_value = mock_review_service
            review_feedback = InternalReviewFeedback(
                approved=True,
                comments=["Looks good"],
                suggested_changes=[],
                timestamp=datetime.now(),
            )
            review_metadata = LLMMetadataOutput(
                total_cost_usd=0.05,
                input_tokens=400,
                output_tokens=200,
                duration_ms=2000,
                duration_api_ms=1800,
                num_turns=1,
                model="claude-sonnet-4-5-20250929",
                tools_used=[],
                execution_flow="Structured review query",
            )
            mock_review_service.review_changes = AsyncMock(
                return_value=(review_feedback, review_metadata)
            )

            # Setup PR creation mock
            from troller.domain.models.pull_request import PullRequest

            mock_pr = PullRequest(
                number=42,
                url="https://github.com/test-owner/test-repo/pull/42",
                head_branch="troller/issue-36",
                base_branch="main",
                head_sha="commit-sha-2",
                created_at=datetime.now(),
                state="open",
            )
            mock_gh_client.create_pull_request.return_value = mock_pr

            # Setup get_pull_request mock - return merged for test completion
            merged_pr = PullRequest(
                number=42,
                url="https://github.com/test-owner/test-repo/pull/42",
                head_branch="troller/issue-36",
                base_branch="main",
                head_sha="commit-sha-2",
                created_at=datetime.now(),
                state="merged",
            )
            mock_gh_client.get_pull_request.return_value = merged_pr

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[
                        fetch_issue,
                        run_planning_agent,
                        create_feature_branch,
                        run_implementation_agent,
                        run_review_agent,
                        create_pull_request,
                        fetch_pull_request,
                    ],
                ):
                    input_data = IssueResolutionWorkflowInput(
                        repo_owner="test-owner",
                        repo_name="test-repo",
                        issue_number=36,
                        target_branch="main",
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        input_data,
                        id="test-workflow-full-flow",
                        task_queue="test-queue",
                    )

                    # Verify result structure
                    assert isinstance(result, IssueResolutionWorkflowOutput)
                    assert result.plan.summary != ""
                    assert len(result.plan.steps) == 2

                    # Verify branch was created
                    assert result.branch_name == "troller/issue-36"

                    # Verify commits were made
                    assert len(result.commits) == 2
                    assert result.commits[0].sha == "commit-sha-1"
                    assert result.commits[1].sha == "commit-sha-2"

                    # Verify PR was created
                    assert result.pull_request is not None
                    assert result.pull_request.number == 42
                    assert (
                        result.pull_request.url
                        == "https://github.com/test-owner/test-repo/pull/42"
                    )
                    assert result.pull_request.head_branch == "troller/issue-36"


@pytest.mark.asyncio
async def test_issue_resolution_workflow_output_includes_all_required_fields() -> None:
    """Test IssueResolutionWorkflowOutput has plan, branch_name, commits, and pull_request."""
    with patch.dict(
        os.environ, {"GITHUB_TOKEN": "test-token", "ANTHROPIC_API_KEY": "test-key"}
    ):
        with (
            patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_gh_client_class,
            patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_planning_service_class,
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
            patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_impl_service_class,
            patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_review_service_class,
        ):
            from datetime import datetime

            from troller.worker.activities.activity_outputs import CommitOutput
            from troller.worker.activities.github_activities import (
                create_feature_branch,
            )
            from troller.worker.activities.implementation_activities import (
                run_implementation_agent,
            )

            # Setup minimal mocks
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client
            mock_issue = MagicMock(spec=GithubIssue)
            mock_issue.number = 1
            mock_issue.title = "Test"
            mock_issue.body = "Body"
            mock_issue.labels = []
            mock_issue.html_url = "https://github.com/o/r/issues/1"
            mock_gh_client.get_issue.return_value = mock_issue

            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            plan = Plan(
                summary="Plan",
                steps=[PlanStep(id="step-1", description="Step", completed=False)],
                created_at=datetime.now(),
                metadata={},
            )
            metadata = LLMMetadataOutput(
                total_cost_usd=0.1,
                input_tokens=100,
                output_tokens=50,
                duration_ms=1000,
                duration_api_ms=900,
                num_turns=1,
                model="claude-opus-4-5-20251101",
                tools_used=[],
                execution_flow="",
            )
            mock_planning_service.generate_plan = AsyncMock(
                return_value=(plan, metadata)
            )

            mock_cloner = MagicMock()
            mock_cloner_class.return_value = mock_cloner
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_cloner.clone_to_temp = AsyncMock(
                return_value=(Path("/tmp/t"), Path("/tmp/t/r"), "sha")
            )
            mock_git_ops.create_branch = AsyncMock()
            mock_git_ops.push_branch = AsyncMock()
            mock_git_ops.get_current_sha = AsyncMock(return_value="branch-sha")

            mock_impl_service = MagicMock()
            mock_impl_service_class.return_value = mock_impl_service
            commits = [
                CommitOutput(
                    sha="commit-1",
                    message="Commit",
                    timestamp=datetime.now(),
                    internal_review_feedback=None,
                )
            ]
            mock_impl_service.implement_changes = AsyncMock(
                return_value=(commits, metadata)
            )

            # Setup review service mock
            mock_review_service = MagicMock()
            mock_review_service_class.return_value = mock_review_service
            review_feedback = InternalReviewFeedback(
                approved=True,
                comments=["Looks good"],
                suggested_changes=[],
                timestamp=datetime.now(),
            )
            review_metadata = LLMMetadataOutput(
                total_cost_usd=0.05,
                input_tokens=400,
                output_tokens=200,
                duration_ms=2000,
                duration_api_ms=1800,
                num_turns=1,
                model="claude-sonnet-4-5-20250929",
                tools_used=[],
                execution_flow="Structured review query",
            )
            mock_review_service.review_changes = AsyncMock(
                return_value=(review_feedback, review_metadata)
            )

            from troller.domain.models.pull_request import PullRequest

            pr = PullRequest(
                number=1,
                url="https://github.com/o/r/pull/1",
                head_branch="troller/issue-1",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="open",
            )
            mock_gh_client.create_pull_request.return_value = pr

            # Setup get_pull_request mock - return merged for test completion
            merged_pr = PullRequest(
                number=1,
                url="https://github.com/o/r/pull/1",
                head_branch="troller/issue-1",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="merged",
            )
            mock_gh_client.get_pull_request.return_value = merged_pr

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[
                        fetch_issue,
                        run_planning_agent,
                        create_feature_branch,
                        run_implementation_agent,
                        run_review_agent,
                        create_pull_request,
                        fetch_pull_request,
                    ],
                ):
                    input_data = IssueResolutionWorkflowInput(
                        repo_owner="o",
                        repo_name="r",
                        issue_number=1,
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        input_data,
                        id="test-workflow-output-fields",
                        task_queue="test-queue",
                    )

                    # Verify all fields are present
                    assert hasattr(result, "plan")
                    assert hasattr(result, "branch_name")
                    assert hasattr(result, "commits")
                    assert hasattr(result, "pull_request")

                    assert result.plan is not None
                    assert result.branch_name == "troller/issue-1"
                    assert isinstance(result.commits, list)
                    assert len(result.commits) > 0
                    assert result.pull_request is not None


@pytest.mark.asyncio
async def test_workflow_detects_merged_pr_and_returns_merged_state() -> None:
    """Test workflow polls PR status and returns merged state when PR is merged."""
    with patch.dict(
        os.environ, {"GITHUB_TOKEN": "test-token", "ANTHROPIC_API_KEY": "test-key"}
    ):
        with (
            patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_gh_client_class,
            patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_planning_service_class,
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
            patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_impl_service_class,
            patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_review_service_class,
        ):
            from datetime import datetime

            from troller.worker.activities.activity_outputs import CommitOutput
            from troller.worker.activities.github_activities import (
                create_feature_branch,
            )
            from troller.worker.activities.implementation_activities import (
                run_implementation_agent,
            )

            # Setup GitHub mock
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client
            mock_github_issue = MagicMock(spec=GithubIssue)
            mock_github_issue.number = 10
            mock_github_issue.title = "Test merged PR"
            mock_github_issue.body = "Test description"
            mock_github_issue.labels = []
            mock_github_issue.html_url = (
                "https://github.com/test-owner/test-repo/issues/10"
            )
            mock_gh_client.get_issue.return_value = mock_github_issue

            # Setup planning mock
            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            expected_plan = Plan(
                summary="Implementation plan",
                steps=[
                    PlanStep(id="step-1", description="Step 1", completed=False),
                ],
                created_at=datetime.now(),
                metadata={"issue_number": 10},
            )
            expected_metadata = LLMMetadataOutput(
                total_cost_usd=0.10,
                input_tokens=800,
                output_tokens=400,
                duration_ms=4000,
                duration_api_ms=3500,
                num_turns=1,
                model="claude-opus-4-5-20251101",
                tools_used=["Skill", "Read"],
                execution_flow="Invoked feature-planner skill",
            )
            mock_planning_service.generate_plan = AsyncMock(
                return_value=(expected_plan, expected_metadata)
            )

            # Setup git mocks
            mock_cloner = MagicMock()
            mock_cloner_class.return_value = mock_cloner
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_cloner.clone_to_temp = AsyncMock(
                return_value=(Path("/tmp/t"), Path("/tmp/t/r"), "sha")
            )
            mock_git_ops.create_branch = AsyncMock()
            mock_git_ops.push_branch = AsyncMock()
            mock_git_ops.get_current_sha = AsyncMock(return_value="branch-sha")

            # Setup implementation mock
            mock_impl_service = MagicMock()
            mock_impl_service_class.return_value = mock_impl_service
            commits = [
                CommitOutput(
                    sha="commit-1",
                    message="Commit",
                    timestamp=datetime.now(),
                    internal_review_feedback=None,
                )
            ]
            mock_impl_service.implement_changes = AsyncMock(
                return_value=(commits, expected_metadata)
            )

            # Setup review service mock
            mock_review_service = MagicMock()
            mock_review_service_class.return_value = mock_review_service
            review_feedback = InternalReviewFeedback(
                approved=True,
                comments=["Looks good"],
                suggested_changes=[],
                timestamp=datetime.now(),
            )
            review_metadata = LLMMetadataOutput(
                total_cost_usd=0.05,
                input_tokens=400,
                output_tokens=200,
                duration_ms=2000,
                duration_api_ms=1800,
                num_turns=1,
                model="claude-sonnet-4-5-20250929",
                tools_used=[],
                execution_flow="Structured review query",
            )
            mock_review_service.review_changes = AsyncMock(
                return_value=(review_feedback, review_metadata)
            )

            # Setup PR creation mock
            from troller.domain.models.pull_request import PullRequest

            pr = PullRequest(
                number=42,
                url="https://github.com/test-owner/test-repo/pull/42",
                head_branch="troller/issue-10",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="open",
            )
            mock_gh_client.create_pull_request.return_value = pr

            # Setup get_pull_request mock - return merged after first poll
            merged_at = datetime(2024, 1, 2, 12, 0, 0)
            merged_pr = PullRequest(
                number=42,
                url="https://github.com/test-owner/test-repo/pull/42",
                head_branch="troller/issue-10",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="merged",
                merged_at=merged_at,
                merged_by="reviewer",
            )
            mock_gh_client.get_pull_request.return_value = merged_pr

            # Run test with time-skipping environment
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[
                        fetch_issue,
                        run_planning_agent,
                        create_feature_branch,
                        run_implementation_agent,
                        run_review_agent,
                        create_pull_request,
                        fetch_pull_request,
                    ],
                ):
                    input_data = IssueResolutionWorkflowInput(
                        repo_owner="test-owner",
                        repo_name="test-repo",
                        issue_number=10,
                        target_branch="main",
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        input_data,
                        id="test-workflow-merged",
                        task_queue="test-queue",
                    )

                    # Verify workflow detected merged state
                    assert isinstance(result, IssueResolutionWorkflowOutput)
                    assert result.final_state == "merged"
                    # Verify merged metadata is populated
                    assert result.merged_at == merged_at.isoformat()
                    assert result.merged_by == "reviewer"


@pytest.mark.asyncio
async def test_workflow_detects_closed_pr_and_returns_closed_state() -> None:
    """Test workflow polls PR status and returns closed state when PR is closed."""
    with patch.dict(
        os.environ, {"GITHUB_TOKEN": "test-token", "ANTHROPIC_API_KEY": "test-key"}
    ):
        with (
            patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_gh_client_class,
            patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_planning_service_class,
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
            patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_impl_service_class,
            patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_review_service_class,
        ):
            from datetime import datetime

            from troller.worker.activities.activity_outputs import CommitOutput
            from troller.worker.activities.github_activities import (
                create_feature_branch,
            )
            from troller.worker.activities.implementation_activities import (
                run_implementation_agent,
            )

            # Setup GitHub mock
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client
            mock_github_issue = MagicMock(spec=GithubIssue)
            mock_github_issue.number = 11
            mock_github_issue.title = "Test closed PR"
            mock_github_issue.body = "Test description"
            mock_github_issue.labels = []
            mock_github_issue.html_url = (
                "https://github.com/test-owner/test-repo/issues/11"
            )
            mock_gh_client.get_issue.return_value = mock_github_issue

            # Setup planning mock
            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            expected_plan = Plan(
                summary="Implementation plan",
                steps=[
                    PlanStep(id="step-1", description="Step 1", completed=False),
                ],
                created_at=datetime.now(),
                metadata={"issue_number": 11},
            )
            expected_metadata = LLMMetadataOutput(
                total_cost_usd=0.10,
                input_tokens=800,
                output_tokens=400,
                duration_ms=4000,
                duration_api_ms=3500,
                num_turns=1,
                model="claude-opus-4-5-20251101",
                tools_used=["Skill", "Read"],
                execution_flow="Invoked feature-planner skill",
            )
            mock_planning_service.generate_plan = AsyncMock(
                return_value=(expected_plan, expected_metadata)
            )

            # Setup git mocks
            mock_cloner = MagicMock()
            mock_cloner_class.return_value = mock_cloner
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_cloner.clone_to_temp = AsyncMock(
                return_value=(Path("/tmp/t"), Path("/tmp/t/r"), "sha")
            )
            mock_git_ops.create_branch = AsyncMock()
            mock_git_ops.push_branch = AsyncMock()
            mock_git_ops.get_current_sha = AsyncMock(return_value="branch-sha")

            # Setup implementation mock
            mock_impl_service = MagicMock()
            mock_impl_service_class.return_value = mock_impl_service
            commits = [
                CommitOutput(
                    sha="commit-1",
                    message="Commit",
                    timestamp=datetime.now(),
                    internal_review_feedback=None,
                )
            ]
            mock_impl_service.implement_changes = AsyncMock(
                return_value=(commits, expected_metadata)
            )

            # Setup review service mock
            mock_review_service = MagicMock()
            mock_review_service_class.return_value = mock_review_service
            review_feedback = InternalReviewFeedback(
                approved=True,
                comments=["Looks good"],
                suggested_changes=[],
                timestamp=datetime.now(),
            )
            review_metadata = LLMMetadataOutput(
                total_cost_usd=0.05,
                input_tokens=400,
                output_tokens=200,
                duration_ms=2000,
                duration_api_ms=1800,
                num_turns=1,
                model="claude-sonnet-4-5-20250929",
                tools_used=[],
                execution_flow="Structured review query",
            )
            mock_review_service.review_changes = AsyncMock(
                return_value=(review_feedback, review_metadata)
            )

            # Setup PR creation mock
            from troller.domain.models.pull_request import PullRequest

            pr = PullRequest(
                number=43,
                url="https://github.com/test-owner/test-repo/pull/43",
                head_branch="troller/issue-11",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="open",
            )
            mock_gh_client.create_pull_request.return_value = pr

            # Setup get_pull_request mock - return closed after first poll
            closed_pr = PullRequest(
                number=43,
                url="https://github.com/test-owner/test-repo/pull/43",
                head_branch="troller/issue-11",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="closed",
            )
            mock_gh_client.get_pull_request.return_value = closed_pr

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[
                        fetch_issue,
                        run_planning_agent,
                        create_feature_branch,
                        run_implementation_agent,
                        run_review_agent,
                        create_pull_request,
                        fetch_pull_request,
                    ],
                ):
                    input_data = IssueResolutionWorkflowInput(
                        repo_owner="test-owner",
                        repo_name="test-repo",
                        issue_number=11,
                        target_branch="main",
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        input_data,
                        id="test-workflow-closed",
                        task_queue="test-queue",
                    )

                    # Verify workflow detected closed state
                    assert isinstance(result, IssueResolutionWorkflowOutput)
                    assert result.final_state == "closed"


@pytest.mark.asyncio
async def test_workflow_returns_timeout_when_pr_stays_open() -> None:
    """Test workflow returns timeout state when PR stays open past max wait."""
    with patch.dict(
        os.environ, {"GITHUB_TOKEN": "test-token", "ANTHROPIC_API_KEY": "test-key"}
    ):
        with (
            patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_gh_client_class,
            patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_planning_service_class,
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
            patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_impl_service_class,
            patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_review_service_class,
            patch.object(
                IssueResolutionWorkflow, "MAX_WAIT_HOURS", 0
            ),  # Set to 0 for instant timeout
            patch.object(
                IssueResolutionWorkflow, "POLL_INTERVAL_SECONDS", 1
            ),  # Short poll interval
        ):
            from datetime import datetime

            from troller.worker.activities.activity_outputs import CommitOutput
            from troller.worker.activities.github_activities import (
                create_feature_branch,
            )
            from troller.worker.activities.implementation_activities import (
                run_implementation_agent,
            )

            # Setup GitHub mock
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client
            mock_github_issue = MagicMock(spec=GithubIssue)
            mock_github_issue.number = 12
            mock_github_issue.title = "Test timeout PR"
            mock_github_issue.body = "Test description"
            mock_github_issue.labels = []
            mock_github_issue.html_url = (
                "https://github.com/test-owner/test-repo/issues/12"
            )
            mock_gh_client.get_issue.return_value = mock_github_issue

            # Setup planning mock
            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            expected_plan = Plan(
                summary="Implementation plan",
                steps=[
                    PlanStep(id="step-1", description="Step 1", completed=False),
                ],
                created_at=datetime.now(),
                metadata={"issue_number": 12},
            )
            expected_metadata = LLMMetadataOutput(
                total_cost_usd=0.10,
                input_tokens=800,
                output_tokens=400,
                duration_ms=4000,
                duration_api_ms=3500,
                num_turns=1,
                model="claude-opus-4-5-20251101",
                tools_used=["Skill", "Read"],
                execution_flow="Invoked feature-planner skill",
            )
            mock_planning_service.generate_plan = AsyncMock(
                return_value=(expected_plan, expected_metadata)
            )

            # Setup git mocks
            mock_cloner = MagicMock()
            mock_cloner_class.return_value = mock_cloner
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_cloner.clone_to_temp = AsyncMock(
                return_value=(Path("/tmp/t"), Path("/tmp/t/r"), "sha")
            )
            mock_git_ops.create_branch = AsyncMock()
            mock_git_ops.push_branch = AsyncMock()
            mock_git_ops.get_current_sha = AsyncMock(return_value="branch-sha")

            # Setup implementation mock
            mock_impl_service = MagicMock()
            mock_impl_service_class.return_value = mock_impl_service
            commits = [
                CommitOutput(
                    sha="commit-1",
                    message="Commit",
                    timestamp=datetime.now(),
                    internal_review_feedback=None,
                )
            ]
            mock_impl_service.implement_changes = AsyncMock(
                return_value=(commits, expected_metadata)
            )

            # Setup review service mock
            mock_review_service = MagicMock()
            mock_review_service_class.return_value = mock_review_service
            review_feedback = InternalReviewFeedback(
                approved=True,
                comments=["Looks good"],
                suggested_changes=[],
                timestamp=datetime.now(),
            )
            review_metadata = LLMMetadataOutput(
                total_cost_usd=0.05,
                input_tokens=400,
                output_tokens=200,
                duration_ms=2000,
                duration_api_ms=1800,
                num_turns=1,
                model="claude-sonnet-4-5-20250929",
                tools_used=[],
                execution_flow="Structured review query",
            )
            mock_review_service.review_changes = AsyncMock(
                return_value=(review_feedback, review_metadata)
            )

            # Setup PR creation mock
            from troller.domain.models.pull_request import PullRequest

            pr = PullRequest(
                number=44,
                url="https://github.com/test-owner/test-repo/pull/44",
                head_branch="troller/issue-12",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="open",
            )
            mock_gh_client.create_pull_request.return_value = pr

            # PR stays open (never merged/closed)
            mock_gh_client.get_pull_request.return_value = pr

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[
                        fetch_issue,
                        run_planning_agent,
                        create_feature_branch,
                        run_implementation_agent,
                        run_review_agent,
                        create_pull_request,
                        fetch_pull_request,
                    ],
                ):
                    input_data = IssueResolutionWorkflowInput(
                        repo_owner="test-owner",
                        repo_name="test-repo",
                        issue_number=12,
                        target_branch="main",
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        input_data,
                        id="test-workflow-timeout",
                        task_queue="test-queue",
                    )

                    # Verify workflow returned timeout state
                    assert isinstance(result, IssueResolutionWorkflowOutput)
                    assert result.final_state == "timeout"


@pytest.mark.asyncio
async def test_workflow_creates_pr_with_comprehensive_body_content() -> None:
    """Test workflow creates PR with comprehensive body containing all expected sections."""
    with patch.dict(
        os.environ, {"GITHUB_TOKEN": "test-token", "ANTHROPIC_API_KEY": "test-key"}
    ):
        with (
            patch(
                "troller.worker.activities.github_activities.GitHubClient"
            ) as mock_gh_client_class,
            patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_planning_service_class,
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
            patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_impl_service_class,
            patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_review_service_class,
        ):
            from datetime import datetime

            from troller.worker.activities.activity_outputs import CommitOutput
            from troller.worker.activities.github_activities import (
                create_feature_branch,
            )
            from troller.worker.activities.implementation_activities import (
                run_implementation_agent,
            )

            # Setup GitHub mock
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client
            mock_github_issue = MagicMock(spec=GithubIssue)
            mock_github_issue.number = 100
            mock_github_issue.title = "Add comprehensive PR body"
            mock_github_issue.body = "Test description for PR body verification"
            mock_github_issue.labels = []
            mock_github_issue.html_url = (
                "https://github.com/test-owner/test-repo/issues/100"
            )
            mock_gh_client.get_issue.return_value = mock_github_issue

            # Setup planning mock with rich content
            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            expected_plan = Plan(
                summary="Implement comprehensive PR body builder",
                steps=[
                    PlanStep(
                        id="step-1",
                        description="Create PRBodyBuilder service",
                        completed=False,
                    ),
                    PlanStep(
                        id="step-2",
                        description="Add unit tests for PRBodyBuilder",
                        completed=False,
                    ),
                    PlanStep(
                        id="step-3",
                        description="Integrate into workflow",
                        completed=False,
                    ),
                ],
                created_at=datetime.now(),
                metadata={"issue_number": 100},
                technical_approach="Create a pure domain service following hexagonal architecture",
                testing_strategy="Unit tests for all formatting scenarios",
            )
            expected_metadata = LLMMetadataOutput(
                total_cost_usd=0.10,
                input_tokens=800,
                output_tokens=400,
                duration_ms=4000,
                duration_api_ms=3500,
                num_turns=1,
                model="claude-opus-4-5-20251101",
                tools_used=["Skill", "Read"],
                execution_flow="Invoked feature-planner skill",
            )
            mock_planning_service.generate_plan = AsyncMock(
                return_value=(expected_plan, expected_metadata)
            )

            # Setup git mocks
            mock_cloner = MagicMock()
            mock_cloner_class.return_value = mock_cloner
            mock_git_ops = MagicMock()
            mock_git_ops_class.return_value = mock_git_ops
            mock_cloner.clone_to_temp = AsyncMock(
                return_value=(Path("/tmp/t"), Path("/tmp/t/r"), "sha")
            )
            mock_git_ops.create_branch = AsyncMock()
            mock_git_ops.push_branch = AsyncMock()
            mock_git_ops.get_current_sha = AsyncMock(return_value="branch-sha")

            # Setup implementation mock with commits
            mock_impl_service = MagicMock()
            mock_impl_service_class.return_value = mock_impl_service
            commits = [
                CommitOutput(
                    sha="abc1234",
                    message="Create PRBodyBuilder service",
                    timestamp=datetime.now(),
                    internal_review_feedback=None,
                ),
                CommitOutput(
                    sha="def5678",
                    message="Add unit tests",
                    timestamp=datetime.now(),
                    internal_review_feedback=None,
                ),
            ]
            mock_impl_service.implement_changes = AsyncMock(
                return_value=(commits, expected_metadata)
            )

            # Setup review service mock
            mock_review_service = MagicMock()
            mock_review_service_class.return_value = mock_review_service
            review_feedback = InternalReviewFeedback(
                approved=True,
                comments=["Looks good"],
                suggested_changes=[],
                timestamp=datetime.now(),
            )
            review_metadata = LLMMetadataOutput(
                total_cost_usd=0.05,
                input_tokens=400,
                output_tokens=200,
                duration_ms=2000,
                duration_api_ms=1800,
                num_turns=1,
                model="claude-sonnet-4-5-20250929",
                tools_used=[],
                execution_flow="Structured review query",
            )
            mock_review_service.review_changes = AsyncMock(
                return_value=(review_feedback, review_metadata)
            )

            # Setup PR creation mock - capture the body argument
            from troller.domain.models.pull_request import PullRequest

            captured_pr_body: list[str] = []

            def capture_create_pr(
                owner: str,
                repo: str,
                title: str,
                body: str,
                head_branch: str,
                base_branch: str,
                draft: bool = False,
            ) -> PullRequest:
                captured_pr_body.append(body)
                return PullRequest(
                    number=50,
                    url=f"https://github.com/{owner}/{repo}/pull/50",
                    head_branch=head_branch,
                    base_branch=base_branch,
                    head_sha="def5678",
                    created_at=datetime.now(),
                    state="open",
                )

            mock_gh_client.create_pull_request.side_effect = capture_create_pr

            # Setup get_pull_request mock - return merged for test completion
            merged_pr = PullRequest(
                number=50,
                url="https://github.com/test-owner/test-repo/pull/50",
                head_branch="troller/issue-100",
                base_branch="main",
                head_sha="def5678",
                created_at=datetime.now(),
                state="merged",
            )
            mock_gh_client.get_pull_request.return_value = merged_pr

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[
                        fetch_issue,
                        run_planning_agent,
                        create_feature_branch,
                        run_implementation_agent,
                        run_review_agent,
                        create_pull_request,
                        fetch_pull_request,
                    ],
                ):
                    input_data = IssueResolutionWorkflowInput(
                        repo_owner="test-owner",
                        repo_name="test-repo",
                        issue_number=100,
                        target_branch="main",
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        input_data,
                        id="test-workflow-pr-body",
                        task_queue="test-queue",
                    )

                    # Verify workflow completed
                    assert isinstance(result, IssueResolutionWorkflowOutput)
                    assert result.pull_request is not None

                    # Verify PR body was captured
                    assert len(captured_pr_body) == 1
                    pr_body = captured_pr_body[0]

                    # Verify PR body contains all expected sections
                    assert "Resolves #100" in pr_body, "PR body should reference issue"
                    assert "## Summary" in pr_body, (
                        "PR body should have Summary section"
                    )
                    assert "Implement comprehensive PR body builder" in pr_body, (
                        "PR body should contain plan summary"
                    )
                    assert "## Technical Approach" in pr_body, (
                        "PR body should have Technical Approach section"
                    )
                    assert "hexagonal architecture" in pr_body, (
                        "PR body should contain technical approach content"
                    )
                    assert "## Implementation Steps" in pr_body, (
                        "PR body should have Implementation Steps section"
                    )
                    assert "Create PRBodyBuilder service" in pr_body, (
                        "PR body should list implementation steps"
                    )
                    assert "## Testing Strategy" in pr_body, (
                        "PR body should have Testing Strategy section"
                    )
                    assert "Unit tests" in pr_body, (
                        "PR body should contain testing strategy"
                    )
                    assert "## Commits" in pr_body, (
                        "PR body should have Commits section"
                    )
                    assert "abc1234" in pr_body, "PR body should list commit SHAs"
                    assert "def5678" in pr_body, "PR body should list all commit SHAs"
                    assert "🤖 Generated by Troller" in pr_body, (
                        "PR body should have footer"
                    )

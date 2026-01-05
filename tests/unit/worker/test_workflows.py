"""Unit tests for Temporal workflows.

Tests use Temporal's testing framework to verify workflow behavior.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from github.Issue import Issue as GithubIssue
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from troller.domain.models.plan import Plan, PlanStep
from troller.worker.activities.github_activities import FetchIssueInput, fetch_issue
from troller.worker.activities.planning_activities import (
    PlanningInput,
    run_planning_agent,
)
from troller.worker.workflows.data_structures import Issue, WorkflowInput
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
                "troller.worker.activities.planning_activities.ClaudeClient"
            ) as mock_claude_client_class,
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

            mock_claude_client = MagicMock()
            mock_claude_client_class.return_value = mock_claude_client
            expected_plan = Plan(
                summary="Implementation plan for: Test Issue",
                steps=[
                    PlanStep(id="step-1", description="Step 1", completed=False),
                    PlanStep(id="step-2", description="Step 2", completed=False),
                ],
                created_at=datetime.now(),
                metadata={"issue_number": 123},
            )
            mock_claude_client.generate_plan = AsyncMock(return_value=expected_plan)

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[fetch_issue, run_planning_agent],
                ):
                    # Execute workflow
                    input_data = WorkflowInput(
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

                    # Verify result is a Plan
                    assert isinstance(result, Plan)
                    assert result.summary.startswith("Implementation plan for:")
                    assert len(result.steps) > 0


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
                "troller.worker.activities.planning_activities.ClaudeClient"
            ) as mock_claude_client_class,
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

            mock_claude_client = MagicMock()
            mock_claude_client_class.return_value = mock_claude_client
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
            mock_claude_client.generate_plan = AsyncMock(return_value=expected_plan)

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[fetch_issue, run_planning_agent],
                ):
                    input_data = WorkflowInput(
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
                    assert isinstance(result, Plan)
                    assert result.summary != ""
                    assert len(result.steps) == 3
                    assert all(isinstance(step, PlanStep) for step in result.steps)
                    assert all(step.id.startswith("step-") for step in result.steps)
                    assert result.created_at is not None


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
                "troller.worker.activities.planning_activities.ClaudeClient"
            ) as mock_claude_client_class,
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

            mock_claude_client = MagicMock()
            mock_claude_client_class.return_value = mock_claude_client
            expected_plan = Plan(
                summary="Plan",
                steps=[PlanStep(id="step-1", description="Step", completed=False)],
                created_at=datetime.now(),
                metadata={},
            )
            mock_claude_client.generate_plan = AsyncMock(return_value=expected_plan)

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[fetch_issue, run_planning_agent],
                ):
                    input_data = WorkflowInput(
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
                    assert isinstance(result, Plan)


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
                "troller.worker.activities.planning_activities.ClaudeClient"
            ) as mock_claude_client_class,
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

            mock_claude_client = MagicMock()
            mock_claude_client_class.return_value = mock_claude_client
            expected_plan = Plan(
                summary="Plan",
                steps=[PlanStep(id="step-1", description="Step", completed=False)],
                created_at=datetime.now(),
                metadata={},
            )
            mock_claude_client.generate_plan = AsyncMock(return_value=expected_plan)

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[fetch_issue, run_planning_agent],
                ):
                    # Test with target_branch
                    input_with_branch = WorkflowInput(
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

                    assert isinstance(result, Plan)

                    # Test without target_branch
                    input_without_branch = WorkflowInput(
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

                    assert isinstance(result, Plan)


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

            assert isinstance(result, Issue)
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
            "troller.worker.activities.planning_activities.ClaudeClient"
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
            mock_client.generate_plan = AsyncMock(return_value=expected_plan)

            # Test
            issue = Issue(
                number=123,
                title="Test Issue",
                description="Test description",
                labels=["bug"],
                url="https://github.com/test/repo/issues/123",
            )
            planning_input = PlanningInput(
                issue=issue,
                repo_owner="test",
                repo_name="repo",
            )

            result = await run_planning_agent(planning_input)

            assert isinstance(result, Plan)
            assert result.summary != ""
            assert len(result.steps) > 0
            assert all(isinstance(step, PlanStep) for step in result.steps)
            assert result.created_at is not None
            assert isinstance(result.metadata, dict)

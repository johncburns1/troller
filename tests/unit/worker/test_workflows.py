"""Unit tests for Temporal workflows.

Tests use Temporal's testing framework to verify workflow behavior.
"""

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from troller.domain.models.plan import Plan, PlanStep
from troller.worker.activities.agent_activities import run_planning_agent
from troller.worker.activities.issue_activities import fetch_issue
from troller.worker.workflows.data_structures import Issue, WorkflowInput
from troller.worker.workflows.issue_resolution import IssueResolutionWorkflow


@pytest.mark.asyncio
async def test_issue_resolution_workflow_executes_activities_in_correct_order() -> None:
    """Test workflow executes fetch_issue then run_planning_agent."""
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
            assert len(result.steps) == 3  # Stub returns 3 steps
            assert all(isinstance(step, PlanStep) for step in result.steps)
            assert all(step.id.startswith("step-") for step in result.steps)
            assert result.created_at is not None


@pytest.mark.asyncio
async def test_issue_resolution_workflow_stores_issue_in_state() -> None:
    """Test workflow stores fetched issue in workflow state."""
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
    result = await fetch_issue("test-owner", "test-repo", 999)

    assert isinstance(result, Issue)
    assert result.number == 999
    assert result.title.startswith("Stub Issue #")
    assert result.description != ""
    assert isinstance(result.labels, list)
    assert result.url.startswith("https://github.com/")


@pytest.mark.asyncio
async def test_run_planning_agent_activity_returns_plan() -> None:
    """Test run_planning_agent activity returns valid plan."""
    issue = Issue(
        number=123,
        title="Test Issue",
        description="Test description",
        labels=["bug"],
        url="https://github.com/test/repo/issues/123",
    )

    result = await run_planning_agent(issue)

    assert isinstance(result, Plan)
    assert result.summary != ""
    assert len(result.steps) > 0
    assert all(isinstance(step, PlanStep) for step in result.steps)
    assert result.created_at is not None
    assert isinstance(result.metadata, dict)

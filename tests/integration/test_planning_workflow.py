"""Integration tests for planning workflow.

Tests the full stack: workflow → activities → GitHub API → Claude API → Plan generation.
"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from github.Issue import Issue as GithubIssue
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from troller.domain.models.plan import Plan, PlanStep
from troller.worker.activities.github_activities import fetch_issue
from troller.worker.activities.planning_activities import run_planning_agent
from troller.worker.workflows.data_structures import IssueResolutionWorkflowInput
from troller.worker.workflows.issue_resolution import IssueResolutionWorkflow


@pytest.fixture
def mock_github_issue() -> MagicMock:
    """Create a mock GitHub issue for testing.

    Returns:
        Mocked GitHub issue with realistic data.
    """
    mock_issue = MagicMock(spec=GithubIssue)
    mock_issue.number = 42
    mock_issue.title = "Add user authentication system"
    mock_issue.body = """## Problem Statement
We need to add user authentication to the application.

## Requirements
- JWT-based authentication
- User registration and login
- Password hashing with bcrypt
"""
    mock_issue.labels = []
    mock_issue.html_url = "https://github.com/test-org/test-repo/issues/42"
    return mock_issue


@pytest.fixture
def expected_plan() -> Plan:
    """Create an expected Plan object for testing.

    Returns:
        A realistic Plan object with multiple steps.
    """
    return Plan(
        summary="Implementation plan for: Add user authentication system",
        steps=[
            PlanStep(
                id="step-1",
                description="Create user model and database schema",
                completed=False,
            ),
            PlanStep(
                id="step-2",
                description="Implement password hashing with bcrypt",
                completed=False,
            ),
            PlanStep(
                id="step-3",
                description="Create JWT token generation and validation",
                completed=False,
            ),
            PlanStep(
                id="step-4",
                description="Implement registration and login endpoints",
                completed=False,
            ),
            PlanStep(
                id="step-5",
                description="Add authentication middleware",
                completed=False,
            ),
        ],
        created_at=datetime.now(),
        metadata={
            "issue_number": 42,
            "skill_output": "Full implementation plan text from skill...",
        },
    )


@pytest.mark.asyncio
async def test_planning_workflow_end_to_end(
    mock_github_issue: MagicMock, expected_plan: Plan
) -> None:
    """Workflow executes end-to-end: fetch_issue → run_planning_agent → returns Plan.

    This integration test validates the full workflow orchestration.
    """
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
        ):
            # Setup GitHub client mock
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client
            mock_gh_client.get_issue.return_value = mock_github_issue

            # Setup planning service mock
            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            mock_planning_service.generate_plan = AsyncMock(return_value=expected_plan)

            # Create workflow environment
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-task-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[fetch_issue, run_planning_agent],
                ):
                    # Execute workflow
                    workflow_input = IssueResolutionWorkflowInput(
                        repo_owner="test-org",
                        repo_name="test-repo",
                        issue_number=42,
                    )
                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        workflow_input,
                        id="test-workflow-1",
                        task_queue="test-task-queue",
                    )

                    # Verify workflow returned the plan
                    assert result is not None
                    assert result.summary == expected_plan.summary
                    assert len(result.steps) == len(expected_plan.steps)


@pytest.mark.asyncio
async def test_planning_workflow_validates_plan_metadata() -> None:
    """Workflow validates that Plan includes required metadata.

    Ensures:
    - issue_number is present in Plan.metadata
    - metadata dict is properly structured
    """
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
        ):
            # Setup mocks
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client

            mock_issue = MagicMock(spec=GithubIssue)
            mock_issue.number = 123
            mock_issue.title = "Test issue"
            mock_issue.body = "Test description"
            mock_issue.labels = []
            mock_issue.html_url = "https://github.com/test/test/issues/123"
            mock_gh_client.get_issue.return_value = mock_issue

            test_plan = Plan(
                summary="Test plan",
                steps=[PlanStep(id="step-1", description="Test step", completed=False)],
                created_at=datetime.now(),
                metadata={
                    "issue_number": 123,
                    "skill_output": "Plan from skill execution",
                },
            )

            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            mock_planning_service.generate_plan = AsyncMock(return_value=test_plan)

            # Create workflow environment and execute
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-task-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[fetch_issue, run_planning_agent],
                ):
                    workflow_input = IssueResolutionWorkflowInput(
                        repo_owner="test",
                        repo_name="test",
                        issue_number=123,
                    )
                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        workflow_input,
                        id="test-workflow-metadata",
                        task_queue="test-task-queue",
                    )

                    # Verify metadata
                    assert "issue_number" in result.metadata
                    assert result.metadata["issue_number"] == 123


@pytest.mark.asyncio
async def test_planning_workflow_validates_step_structure() -> None:
    """Workflow validates PlanStep structure.

    Validates:
    - Required fields: id, description, completed
    - Field types are correct
    """
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
        ):
            # Setup mocks
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client

            mock_issue = MagicMock(spec=GithubIssue)
            mock_issue.number = 456
            mock_issue.title = "Test"
            mock_issue.body = "Description"
            mock_issue.labels = []
            mock_issue.html_url = "https://github.com/test/test/issues/456"
            mock_gh_client.get_issue.return_value = mock_issue

            test_plan = Plan(
                summary="Test plan with multiple steps",
                steps=[
                    PlanStep(id="step-1", description="First step", completed=False),
                    PlanStep(id="step-2", description="Second step", completed=False),
                    PlanStep(id="step-3", description="Third step", completed=True),
                ],
                created_at=datetime.now(),
                metadata={"issue_number": 456},
            )

            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            mock_planning_service.generate_plan = AsyncMock(return_value=test_plan)

            # Execute workflow
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-task-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[fetch_issue, run_planning_agent],
                ):
                    workflow_input = IssueResolutionWorkflowInput(
                        repo_owner="test",
                        repo_name="test",
                        issue_number=456,
                    )
                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        workflow_input,
                        id="test-workflow-steps",
                        task_queue="test-task-queue",
                    )

                    # Validate step structure
                    assert len(result.steps) == 3
                    for step in result.steps:
                        # Required fields
                        assert isinstance(step.id, str)
                        assert isinstance(step.description, str)
                        assert isinstance(step.completed, bool)


@pytest.mark.asyncio
async def test_planning_workflow_with_optional_fields() -> None:
    """Workflow handles Plans with various metadata configurations."""
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
        ):
            # Setup mocks
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client

            mock_issue = MagicMock(spec=GithubIssue)
            mock_issue.number = 789
            mock_issue.title = "Feature"
            mock_issue.body = "Add feature"
            mock_issue.labels = []
            mock_issue.html_url = "https://github.com/test/test/issues/789"
            mock_gh_client.get_issue.return_value = mock_issue

            # Plan with rich metadata
            test_plan = Plan(
                summary="Feature implementation",
                steps=[PlanStep(id="step-1", description="Implement", completed=False)],
                created_at=datetime.now(),
                metadata={
                    "issue_number": 789,
                    "skill_output": "Detailed plan from skill execution...",
                    "custom_data": {"complexity": "high", "priority": 1},
                },
            )

            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            mock_planning_service.generate_plan = AsyncMock(return_value=test_plan)

            # Execute workflow
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-task-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[fetch_issue, run_planning_agent],
                ):
                    workflow_input = IssueResolutionWorkflowInput(
                        repo_owner="test",
                        repo_name="test",
                        issue_number=789,
                    )
                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        workflow_input,
                        id="test-workflow-optional",
                        task_queue="test-task-queue",
                    )

                    # Verify metadata preserved
                    assert result.metadata["issue_number"] == 789
                    assert "skill_output" in result.metadata
                    assert "custom_data" in result.metadata

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
from troller.worker.workflows.data_structures import WorkflowInput
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
                related_files=["src/models/user.py", "migrations/001_create_users.sql"],
                estimated_complexity="moderate",
            ),
            PlanStep(
                id="step-2",
                description="Implement password hashing with bcrypt",
                completed=False,
                related_files=["src/auth/password.py"],
                estimated_complexity="simple",
            ),
            PlanStep(
                id="step-3",
                description="Create JWT token generation and validation",
                completed=False,
                related_files=["src/auth/jwt.py"],
                estimated_complexity="moderate",
            ),
            PlanStep(
                id="step-4",
                description="Implement registration and login endpoints",
                completed=False,
                related_files=["src/api/auth.py"],
                estimated_complexity="complex",
            ),
            PlanStep(
                id="step-5",
                description="Add authentication middleware",
                completed=False,
                related_files=["src/middleware/auth.py"],
                estimated_complexity="moderate",
            ),
        ],
        created_at=datetime.now(),
        metadata={
            "issue_number": 42,
            "estimated_total_complexity": "complex",
        },
        technical_approach=(
            "Use JWT for stateless authentication. "
            "Store hashed passwords with bcrypt. "
            "Implement middleware for protecting routes."
        ),
        testing_strategy=(
            "Unit tests for password hashing and JWT functions. "
            "Integration tests for auth endpoints. "
            "End-to-end tests for full authentication flow."
        ),
    )


@pytest.mark.asyncio
async def test_planning_workflow_end_to_end(
    mock_github_issue: MagicMock, expected_plan: Plan
) -> None:
    """Test the complete planning workflow from trigger to plan generation.

    This integration test validates:
    - Workflow executes successfully
    - Activities are called in correct order
    - Plan is returned with expected structure
    - All Plan fields are properly populated
    """
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
            mock_gh_client.get_issue.return_value = mock_github_issue

            # Setup Claude mock
            mock_claude_client = MagicMock()
            mock_claude_client_class.return_value = mock_claude_client
            mock_claude_client.generate_plan = AsyncMock(return_value=expected_plan)

            # Run integration test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="integration-test-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[fetch_issue, run_planning_agent],
                ):
                    # Execute workflow with realistic input
                    workflow_input = WorkflowInput(
                        repo_owner="test-org",
                        repo_name="test-repo",
                        issue_number=42,
                        target_branch="main",
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        workflow_input,
                        id="integration-test-planning-workflow",
                        task_queue="integration-test-queue",
                    )

                    # Verify the result is a Plan instance
                    assert isinstance(result, Plan)

                    # Verify Plan has required fields
                    assert result.summary != ""
                    assert result.summary.startswith("Implementation plan for:")
                    assert len(result.steps) > 0
                    assert result.created_at is not None
                    assert isinstance(result.metadata, dict)

                    # Verify all steps have proper structure
                    for step in result.steps:
                        assert isinstance(step, PlanStep)
                        assert step.id != ""
                        assert step.id.startswith("step-")
                        assert step.description != ""
                        assert isinstance(step.completed, bool)
                        assert (
                            step.completed is False
                        )  # New plans have incomplete steps

                    # Verify GitHub client was called correctly
                    mock_gh_client.get_issue.assert_called_once_with(
                        owner="test-org", repo="test-repo", issue_number=42
                    )

                    # Verify Claude client was called with issue data and repo info
                    mock_claude_client.generate_plan.assert_awaited_once()
                    call_kwargs = mock_claude_client.generate_plan.call_args.kwargs
                    assert call_kwargs["issue_title"] == mock_github_issue.title
                    assert call_kwargs["issue_body"] == mock_github_issue.body
                    assert call_kwargs["issue_number"] == 42
                    assert call_kwargs["repo_owner"] == "test-org"
                    assert call_kwargs["repo_name"] == "test-repo"
                    assert call_kwargs["target_branch"] == "main"


@pytest.mark.asyncio
async def test_planning_workflow_validates_plan_metadata(
    mock_github_issue: MagicMock, expected_plan: Plan
) -> None:
    """Test that the planning workflow returns a plan with proper metadata.

    Validates:
    - Metadata dictionary contains expected keys
    - Metadata values are appropriate types
    """
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
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client
            mock_gh_client.get_issue.return_value = mock_github_issue

            mock_claude_client = MagicMock()
            mock_claude_client_class.return_value = mock_claude_client
            mock_claude_client.generate_plan = AsyncMock(return_value=expected_plan)

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="integration-test-metadata-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[fetch_issue, run_planning_agent],
                ):
                    workflow_input = WorkflowInput(
                        repo_owner="test-org",
                        repo_name="test-repo",
                        issue_number=42,
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        workflow_input,
                        id="integration-test-metadata",
                        task_queue="integration-test-metadata-queue",
                    )

                    # Verify metadata structure
                    assert isinstance(result.metadata, dict)
                    assert "issue_number" in result.metadata
                    assert result.metadata["issue_number"] == 42


@pytest.mark.asyncio
async def test_planning_workflow_validates_step_structure(
    mock_github_issue: MagicMock, expected_plan: Plan
) -> None:
    """Test that plan steps have all required and optional fields.

    Validates:
    - Required fields: id, description, completed
    - Optional fields: related_files, estimated_complexity
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
                "troller.worker.activities.planning_activities.ClaudeClient"
            ) as mock_claude_client_class,
        ):
            # Setup mocks
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client
            mock_gh_client.get_issue.return_value = mock_github_issue

            mock_claude_client = MagicMock()
            mock_claude_client_class.return_value = mock_claude_client
            mock_claude_client.generate_plan = AsyncMock(return_value=expected_plan)

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="integration-test-steps-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[fetch_issue, run_planning_agent],
                ):
                    workflow_input = WorkflowInput(
                        repo_owner="test-org",
                        repo_name="test-repo",
                        issue_number=42,
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        workflow_input,
                        id="integration-test-steps",
                        task_queue="integration-test-steps-queue",
                    )

                    # Validate each step has proper structure
                    assert len(result.steps) > 0

                    for i, step in enumerate(result.steps, start=1):
                        # Required fields
                        assert isinstance(step.id, str)
                        assert step.id != ""
                        assert isinstance(step.description, str)
                        assert step.description != ""
                        assert isinstance(step.completed, bool)

                        # Optional fields - check types if present
                        if step.related_files is not None:
                            assert isinstance(step.related_files, list)
                            assert all(isinstance(f, str) for f in step.related_files)

                        if step.estimated_complexity is not None:
                            assert step.estimated_complexity in [
                                "simple",
                                "moderate",
                                "complex",
                            ]


@pytest.mark.asyncio
async def test_planning_workflow_with_optional_fields(
    mock_github_issue: MagicMock, expected_plan: Plan
) -> None:
    """Test that the workflow handles optional Plan fields correctly.

    Validates:
    - technical_approach is included if provided
    - testing_strategy is included if provided
    - Fields are properly typed strings
    """
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
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client
            mock_gh_client.get_issue.return_value = mock_github_issue

            mock_claude_client = MagicMock()
            mock_claude_client_class.return_value = mock_claude_client
            mock_claude_client.generate_plan = AsyncMock(return_value=expected_plan)

            # Run test
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="integration-test-optional-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[fetch_issue, run_planning_agent],
                ):
                    workflow_input = WorkflowInput(
                        repo_owner="test-org",
                        repo_name="test-repo",
                        issue_number=42,
                    )

                    result = await env.client.execute_workflow(
                        IssueResolutionWorkflow.run,
                        workflow_input,
                        id="integration-test-optional",
                        task_queue="integration-test-optional-queue",
                    )

                    # Verify optional fields are handled correctly
                    if result.technical_approach is not None:
                        assert isinstance(result.technical_approach, str)
                        assert result.technical_approach != ""

                    if result.testing_strategy is not None:
                        assert isinstance(result.testing_strategy, str)
                        assert result.testing_strategy != ""

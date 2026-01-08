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
from troller.worker.activities.activity_outputs import LLMMetadataOutput
from troller.worker.activities.github_activities import (
    create_feature_branch,
    create_pull_request,
    fetch_issue,
)
from troller.worker.activities.implementation_activities import run_implementation_agent
from troller.worker.activities.planning_activities import run_planning_agent
from troller.worker.workflows.data_structures import (
    IssueResolutionWorkflowInput,
    IssueResolutionWorkflowOutput,
)
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
def expected_llm_metadata() -> LLMMetadataOutput:
    """Create expected LLM metadata for testing.

    Returns:
        LLMMetadataOutput with realistic execution information.
    """
    return LLMMetadataOutput(
        total_cost_usd=0.15,
        input_tokens=1000,
        output_tokens=500,
        duration_ms=5000,
        duration_api_ms=4500,
        num_turns=1,
        model="claude-opus-4-5-20251101",
        tools_used=["Skill", "Read", "Grep", "Glob"],
        execution_flow="Invoked feature-planner skill, used Read(15), Grep(8)",
    )


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
    mock_github_issue: MagicMock,
    expected_plan: Plan,
    expected_llm_metadata: LLMMetadataOutput,
) -> None:
    """Workflow executes end-to-end: fetch_issue → branch → PR (draft) → plan → implement.

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
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
            patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_impl_service_class,
        ):
            # Setup GitHub client mock
            mock_gh_client = MagicMock()
            mock_gh_client_class.return_value = mock_gh_client
            mock_gh_client.get_issue.return_value = mock_github_issue

            # Setup planning service mock (returns tuple)
            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            mock_planning_service.generate_plan = AsyncMock(
                return_value=(expected_plan, expected_llm_metadata)
            )

            # Setup git and implementation mocks
            from pathlib import Path

            from troller.domain.models.pull_request import PullRequest
            from troller.worker.activities.activity_outputs import CommitOutput

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
                return_value=(commits, expected_llm_metadata)
            )

            pr = PullRequest(
                number=1,
                url="https://github.com/test-org/test-repo/pull/1",
                head_branch="troller/issue-42",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="open",
            )
            mock_gh_client.create_pull_request.return_value = pr

            # Create workflow environment
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-task-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[
                        fetch_issue,
                        run_planning_agent,
                        create_feature_branch,
                        run_implementation_agent,
                        create_pull_request,
                    ],
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

                    # Verify workflow returned the workflow output
                    assert isinstance(result, IssueResolutionWorkflowOutput)
                    assert result.plan.summary == expected_plan.summary
                    assert len(result.plan.steps) == len(expected_plan.steps)


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
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
            patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_impl_service_class,
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

            # Create test LLM metadata
            test_llm_metadata = LLMMetadataOutput(
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

            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            mock_planning_service.generate_plan = AsyncMock(
                return_value=(test_plan, test_llm_metadata)
            )

            # Setup git and implementation mocks
            from pathlib import Path

            from troller.domain.models.pull_request import PullRequest
            from troller.worker.activities.activity_outputs import CommitOutput

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
                return_value=(commits, test_llm_metadata)
            )

            pr = PullRequest(
                number=1,
                url="https://github.com/test/test/pull/1",
                head_branch="troller/issue-123",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="open",
            )
            mock_gh_client.create_pull_request.return_value = pr

            # Create workflow environment and execute
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-task-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[
                        fetch_issue,
                        run_planning_agent,
                        create_feature_branch,
                        run_implementation_agent,
                        create_pull_request,
                    ],
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
                    assert isinstance(result, IssueResolutionWorkflowOutput)
                    assert "issue_number" in result.plan.metadata
                    assert result.plan.metadata["issue_number"] == 123


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
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
            patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_impl_service_class,
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

            # Create test LLM metadata
            test_llm_metadata = LLMMetadataOutput(
                total_cost_usd=0.12,
                input_tokens=900,
                output_tokens=450,
                duration_ms=4500,
                duration_api_ms=4000,
                num_turns=1,
                model="claude-opus-4-5-20251101",
                tools_used=["Skill", "Read", "Grep"],
                execution_flow="Invoked feature-planner skill",
            )

            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            mock_planning_service.generate_plan = AsyncMock(
                return_value=(test_plan, test_llm_metadata)
            )

            # Setup git and implementation mocks
            from pathlib import Path

            from troller.domain.models.pull_request import PullRequest
            from troller.worker.activities.activity_outputs import CommitOutput

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
                return_value=(commits, test_llm_metadata)
            )

            pr = PullRequest(
                number=1,
                url="https://github.com/test/test/pull/1",
                head_branch="troller/issue-456",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="open",
            )
            mock_gh_client.create_pull_request.return_value = pr

            # Execute workflow
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-task-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[
                        fetch_issue,
                        run_planning_agent,
                        create_feature_branch,
                        run_implementation_agent,
                        create_pull_request,
                    ],
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
                    assert isinstance(result, IssueResolutionWorkflowOutput)
                    assert len(result.plan.steps) == 3
                    for step in result.plan.steps:
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
            patch(
                "troller.worker.activities.github_activities.RepoCloner"
            ) as mock_cloner_class,
            patch(
                "troller.worker.activities.github_activities.GitOperations"
            ) as mock_git_ops_class,
            patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_impl_service_class,
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

            # Create test LLM metadata
            test_llm_metadata = LLMMetadataOutput(
                total_cost_usd=0.20,
                input_tokens=1200,
                output_tokens=600,
                duration_ms=6000,
                duration_api_ms=5500,
                num_turns=1,
                model="claude-opus-4-5-20251101",
                tools_used=["Skill", "Read", "Grep", "Glob"],
                execution_flow="Invoked feature-planner skill, used Read(20)",
            )

            mock_planning_service = MagicMock()
            mock_planning_service_class.return_value = mock_planning_service
            mock_planning_service.generate_plan = AsyncMock(
                return_value=(test_plan, test_llm_metadata)
            )

            # Setup git and implementation mocks
            from pathlib import Path

            from troller.domain.models.pull_request import PullRequest
            from troller.worker.activities.activity_outputs import CommitOutput

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
                return_value=(commits, test_llm_metadata)
            )

            pr = PullRequest(
                number=1,
                url="https://github.com/test/test/pull/1",
                head_branch="troller/issue-789",
                base_branch="main",
                head_sha="commit-1",
                created_at=datetime.now(),
                state="open",
            )
            mock_gh_client.create_pull_request.return_value = pr

            # Execute workflow
            async with await WorkflowEnvironment.start_time_skipping() as env:
                async with Worker(
                    env.client,
                    task_queue="test-task-queue",
                    workflows=[IssueResolutionWorkflow],
                    activities=[
                        fetch_issue,
                        run_planning_agent,
                        create_feature_branch,
                        run_implementation_agent,
                        create_pull_request,
                    ],
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
                    assert isinstance(result, IssueResolutionWorkflowOutput)
                    assert result.plan.metadata["issue_number"] == 789
                    assert "skill_output" in result.plan.metadata
                    assert "custom_data" in result.plan.metadata

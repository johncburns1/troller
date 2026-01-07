"""Unit tests for planning activities."""

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from troller.config import ClaudeModelConfig
from troller.domain.models.plan import Plan, PlanStep
from troller.worker.activities.planning_activities import (
    PlanningInput,
    run_planning_agent,
)
from troller.worker.workflows.data_structures import Issue


class TestRunPlanningAgent:
    """Test suite for run_planning_agent activity."""

    @pytest.mark.asyncio
    async def test_run_planning_agent_returns_plan_object(self) -> None:
        """run_planning_agent returns Plan domain object."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_service_class:
                # Setup mock
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                # Mock plan
                expected_plan = Plan(
                    summary="Test implementation plan",
                    steps=[
                        PlanStep(
                            id="step-1",
                            description="Implement feature",
                            completed=False,
                        )
                    ],
                    created_at=datetime.now(),
                    metadata={"issue_number": 42},
                )
                mock_service.generate_plan = AsyncMock(return_value=expected_plan)

                # Test
                issue = Issue(
                    number=42,
                    title="Add new feature",
                    description="Feature description",
                    labels=["enhancement"],
                    url="https://github.com/owner/repo/issues/42",
                )
                planning_input = PlanningInput(
                    issue=issue,
                    repo_owner="owner",
                    repo_name="repo",
                )
                result = await run_planning_agent(planning_input)

                # Verify
                assert isinstance(result, Plan)
                assert result == expected_plan

    @pytest.mark.asyncio
    async def test_run_planning_agent_calls_service_with_issue_details(self) -> None:
        """run_planning_agent calls PlanningService.generate_plan with issue details."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_service_class:
                # Setup mock
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                mock_plan = Plan(
                    summary="Plan",
                    steps=[],
                    created_at=datetime.now(),
                    metadata={},
                )
                mock_service.generate_plan = AsyncMock(return_value=mock_plan)

                # Test
                issue = Issue(
                    number=123,
                    title="Fix authentication bug",
                    description="Users cannot log in with OAuth",
                    labels=["bug", "priority:high"],
                    url="https://github.com/test/test/issues/123",
                )
                planning_input = PlanningInput(
                    issue=issue,
                    repo_owner="testowner",
                    repo_name="testrepo",
                    target_branch="develop",
                )
                await run_planning_agent(planning_input)

                # Verify
                mock_service.generate_plan.assert_awaited_once_with(
                    issue_title="Fix authentication bug",
                    issue_body="Users cannot log in with OAuth",
                    issue_number=123,
                    repo_owner="testowner",
                    repo_name="testrepo",
                    target_branch="develop",
                )

    @pytest.mark.asyncio
    async def test_run_planning_agent_handles_empty_description(self) -> None:
        """run_planning_agent handles issues with empty descriptions."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_service_class:
                # Setup mock
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                mock_plan = Plan(
                    summary="Plan",
                    steps=[],
                    created_at=datetime.now(),
                    metadata={},
                )
                mock_service.generate_plan = AsyncMock(return_value=mock_plan)

                # Test
                issue = Issue(
                    number=1,
                    title="Issue with no description",
                    description="",
                    labels=[],
                    url="https://github.com/owner/repo/issues/1",
                )
                planning_input = PlanningInput(
                    issue=issue,
                    repo_owner="owner",
                    repo_name="repo",
                )
                result = await run_planning_agent(planning_input)

                # Verify - should still work with empty description
                assert isinstance(result, Plan)
                mock_service.generate_plan.assert_awaited_once_with(
                    issue_title="Issue with no description",
                    issue_body="",
                    issue_number=1,
                    repo_owner="owner",
                    repo_name="repo",
                    target_branch=None,
                )

    @pytest.mark.asyncio
    async def test_run_planning_agent_preserves_plan_structure(self) -> None:
        """run_planning_agent preserves all Plan fields from PlanningService."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_service_class:
                # Setup mock
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                # Complex plan with multiple steps
                expected_plan = Plan(
                    summary="Comprehensive implementation plan",
                    steps=[
                        PlanStep(
                            id="step-1",
                            description="Research existing code",
                            completed=False,
                        ),
                        PlanStep(
                            id="step-2",
                            description="Implement core logic",
                            completed=False,
                        ),
                        PlanStep(
                            id="step-3",
                            description="Add tests",
                            completed=False,
                        ),
                    ],
                    created_at=datetime(2025, 1, 1, 12, 0, 0),
                    metadata={"issue_number": 999, "custom_field": "value"},
                )
                mock_service.generate_plan = AsyncMock(return_value=expected_plan)

                # Test
                issue = Issue(
                    number=999,
                    title="Major refactoring",
                    description="Refactor authentication system",
                    labels=["refactoring"],
                    url="https://github.com/owner/repo/issues/999",
                )
                planning_input = PlanningInput(
                    issue=issue,
                    repo_owner="owner",
                    repo_name="repo",
                )
                result = await run_planning_agent(planning_input)

                # Verify all fields preserved
                assert result.summary == "Comprehensive implementation plan"
                assert len(result.steps) == 3
                assert result.steps[0].id == "step-1"
                assert result.steps[1].description == "Implement core logic"
                assert result.steps[2].description == "Add tests"
                assert result.created_at == datetime(2025, 1, 1, 12, 0, 0)
                assert result.metadata == {"issue_number": 999, "custom_field": "value"}

    @pytest.mark.asyncio
    async def test_run_planning_agent_passes_config_model_to_claude_client(
        self,
    ) -> None:
        """run_planning_agent passes config.claude.planning_model to ClaudeClient."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.planning_activities.ClaudeClient"
            ) as mock_client_class:
                with patch(
                    "troller.worker.activities.planning_activities.config"
                ) as mock_config:
                    # Setup mock config
                    mock_claude_config = ClaudeModelConfig()
                    mock_claude_config.planning_model = "claude-opus-custom"
                    mock_config.claude = mock_claude_config

                    # Setup mock client and service
                    mock_client = MagicMock()
                    mock_client_class.return_value = mock_client

                    with patch(
                        "troller.worker.activities.planning_activities.PlanningService"
                    ) as mock_service_class:
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service
                        mock_plan = Plan(
                            summary="Test",
                            steps=[],
                            created_at=datetime.now(),
                            metadata={},
                        )
                        mock_service.generate_plan = AsyncMock(return_value=mock_plan)

                        # Test
                        issue = Issue(
                            number=1,
                            title="Test",
                            description="Test",
                            labels=[],
                            url="https://github.com/test/test/issues/1",
                        )
                        planning_input = PlanningInput(
                            issue=issue, repo_owner="test", repo_name="test"
                        )
                        await run_planning_agent(planning_input)

                        # Verify ClaudeClient was created with planning model
                        mock_client_class.assert_called_once_with(
                            model="claude-opus-custom"
                        )

    @pytest.mark.asyncio
    async def test_run_planning_agent_uses_environment_variable_for_model(self) -> None:
        """run_planning_agent respects CLAUDE_PLANNING_MODEL environment variable."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "test-key",
                "CLAUDE_PLANNING_MODEL": "claude-opus-from-env",
            },
        ):
            with patch(
                "troller.worker.activities.planning_activities.ClaudeClient"
            ) as mock_client_class:
                with patch(
                    "troller.worker.activities.planning_activities.config"
                ) as mock_config:
                    # Setup mock config to reflect environment variable
                    mock_claude_config = ClaudeModelConfig(
                        planning_model="claude-opus-from-env"
                    )
                    mock_config.claude = mock_claude_config

                    # Setup mock client and service
                    mock_client = MagicMock()
                    mock_client_class.return_value = mock_client

                    with patch(
                        "troller.worker.activities.planning_activities.PlanningService"
                    ) as mock_service_class:
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service
                        mock_plan = Plan(
                            summary="Test",
                            steps=[],
                            created_at=datetime.now(),
                            metadata={},
                        )
                        mock_service.generate_plan = AsyncMock(return_value=mock_plan)

                        # Test
                        issue = Issue(
                            number=1,
                            title="Test",
                            description="Test",
                            labels=[],
                            url="https://github.com/test/test/issues/1",
                        )
                        planning_input = PlanningInput(
                            issue=issue, repo_owner="test", repo_name="test"
                        )
                        await run_planning_agent(planning_input)

                        # Verify ClaudeClient was created with environment model
                        mock_client_class.assert_called_once_with(
                            model="claude-opus-from-env"
                        )

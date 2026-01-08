"""Unit tests for planning activities."""

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from troller.config import ClaudeModelConfig
from troller.domain.models.plan import Plan, PlanStep
from troller.worker.activities.activity_outputs import LLMMetadataOutput
from troller.worker.activities.planning_activities import (
    PlanningActivityOutput,
    PlanningInput,
    run_planning_agent,
)


class TestRunPlanningAgent:
    """Test suite for run_planning_agent activity."""

    @pytest.mark.asyncio
    async def test_run_planning_agent_returns_plan_object(self) -> None:
        """run_planning_agent returns PlanDTO."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.planning_activities.PlanningService"
            ) as mock_service_class:
                # Setup mock
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                # Mock plan and metadata (domain models from service)
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
                mock_service.generate_plan = AsyncMock(
                    return_value=(expected_plan, expected_metadata)
                )

                # Test with DTO input
                planning_input = PlanningInput(
                    issue_number=42,
                    issue_title="Add new feature",
                    issue_description="Feature description",
                    issue_labels=["enhancement"],
                    issue_url="https://github.com/owner/repo/issues/42",
                    repo_owner="owner",
                    repo_name="repo",
                )
                result = await run_planning_agent(planning_input)

                # Verify activity returns DTOs
                assert isinstance(result, PlanningActivityOutput)
                assert result.plan.summary == expected_plan.summary
                assert len(result.plan.steps) == 1
                assert result.plan.steps[0].id == "step-1"
                assert result.llm_metadata.total_cost_usd == 0.10

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
                mock_metadata = LLMMetadataOutput(
                    total_cost_usd=0.05,
                    input_tokens=500,
                    output_tokens=250,
                    duration_ms=2000,
                    duration_api_ms=1800,
                    num_turns=1,
                    model="claude-opus-4-5-20251101",
                    tools_used=["Skill"],
                    execution_flow="Invoked feature-planner skill",
                )
                mock_service.generate_plan = AsyncMock(
                    return_value=(mock_plan, mock_metadata)
                )

                # Test with DTO input
                planning_input = PlanningInput(
                    issue_number=123,
                    issue_title="Fix authentication bug",
                    issue_description="Users cannot log in with OAuth",
                    issue_labels=["bug", "priority:high"],
                    issue_url="https://github.com/test/test/issues/123",
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
                mock_metadata = LLMMetadataOutput(
                    total_cost_usd=0.03,
                    input_tokens=300,
                    output_tokens=150,
                    duration_ms=1500,
                    duration_api_ms=1300,
                    num_turns=1,
                    model="claude-opus-4-5-20251101",
                    tools_used=[],
                    execution_flow="Executed planning task",
                )
                mock_service.generate_plan = AsyncMock(
                    return_value=(mock_plan, mock_metadata)
                )

                # Test
                planning_input = PlanningInput(
                    issue_number=1,
                    issue_title="Issue with no description",
                    issue_description="",
                    issue_labels=[],
                    issue_url="https://github.com/owner/repo/issues/1",
                    repo_owner="owner",
                    repo_name="repo",
                )
                result = await run_planning_agent(planning_input)

                # Verify - should still work with empty description
                assert isinstance(result, PlanningActivityOutput)
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
                expected_metadata = LLMMetadataOutput(
                    total_cost_usd=0.25,
                    input_tokens=1500,
                    output_tokens=750,
                    duration_ms=7000,
                    duration_api_ms=6500,
                    num_turns=1,
                    model="claude-opus-4-5-20251101",
                    tools_used=["Skill", "Read", "Grep", "Glob"],
                    execution_flow="Invoked feature-planner skill, used Read(25)",
                )
                mock_service.generate_plan = AsyncMock(
                    return_value=(expected_plan, expected_metadata)
                )

                # Test
                planning_input = PlanningInput(
                    issue_number=999,
                    issue_title="Major refactoring",
                    issue_description="Refactor authentication system",
                    issue_labels=["refactoring"],
                    issue_url="https://github.com/owner/repo/issues/999",
                    repo_owner="owner",
                    repo_name="repo",
                )
                result = await run_planning_agent(planning_input)

                # Verify all fields preserved
                assert result.plan.summary == "Comprehensive implementation plan"
                assert len(result.plan.steps) == 3
                assert result.plan.steps[0].id == "step-1"
                assert result.plan.steps[1].description == "Implement core logic"
                assert result.plan.steps[2].description == "Add tests"
                assert result.plan.created_at == datetime(2025, 1, 1, 12, 0, 0)
                assert result.plan.metadata == {
                    "issue_number": 999,
                    "custom_field": "value",
                }

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
                        mock_metadata = LLMMetadataOutput(
                            total_cost_usd=0.01,
                            input_tokens=100,
                            output_tokens=50,
                            duration_ms=1000,
                            duration_api_ms=900,
                            num_turns=1,
                            model="claude-opus-custom",
                            tools_used=[],
                            execution_flow="Executed",
                        )
                        mock_service.generate_plan = AsyncMock(
                            return_value=(mock_plan, mock_metadata)
                        )

                        # Test
                        planning_input = PlanningInput(
                            issue_number=1,
                            issue_title="Test",
                            issue_description="Test",
                            issue_labels=[],
                            issue_url="https://github.com/test/test/issues/1",
                            repo_owner="test",
                            repo_name="test",
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
                        mock_metadata = LLMMetadataOutput(
                            total_cost_usd=0.01,
                            input_tokens=100,
                            output_tokens=50,
                            duration_ms=1000,
                            duration_api_ms=900,
                            num_turns=1,
                            model="claude-opus-from-env",
                            tools_used=[],
                            execution_flow="Executed",
                        )
                        mock_service.generate_plan = AsyncMock(
                            return_value=(mock_plan, mock_metadata)
                        )

                        # Test
                        planning_input = PlanningInput(
                            issue_number=1,
                            issue_title="Test",
                            issue_description="Test",
                            issue_labels=[],
                            issue_url="https://github.com/test/test/issues/1",
                            repo_owner="test",
                            repo_name="test",
                        )
                        await run_planning_agent(planning_input)

                        # Verify ClaudeClient was created with environment model
                        mock_client_class.assert_called_once_with(
                            model="claude-opus-from-env"
                        )

"""Unit tests for implementation activities."""

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from troller.config import ClaudeModelConfig
from troller.domain.models.commit import Commit
from troller.domain.models.issue import Issue
from troller.domain.models.plan import Plan
from troller.worker.activities.activity_outputs import (
    LLMMetadataOutput,
    PlanOutput,
    PlanStepOutput,
)
from troller.worker.activities.implementation_activities import (
    ImplementationActivityOutput,
    ImplementationInput,
    run_implementation_agent,
)


class TestRunImplementationAgent:
    """Test suite for run_implementation_agent activity."""

    @pytest.mark.asyncio
    async def test_run_implementation_agent_returns_commits(self) -> None:
        """run_implementation_agent returns ImplementationActivityOutput with commits."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_service_class:
                # Setup mock
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                # Mock commits and metadata (domain models from service)
                expected_commit = Commit(
                    sha="abc123def456",
                    message="Implement feature X",
                    timestamp=datetime.now(),
                )
                expected_metadata = LLMMetadataOutput(
                    total_cost_usd=0.15,
                    input_tokens=1200,
                    output_tokens=600,
                    duration_ms=6000,
                    duration_api_ms=5500,
                    num_turns=1,
                    model="claude-sonnet-4-5-20250929",
                    tools_used=["Skill", "Read", "Write"],
                    execution_flow="Invoked feature-implementation skill",
                )
                mock_service.implement_changes = AsyncMock(
                    return_value=([expected_commit], expected_metadata)
                )

                # Create test input with DTOs
                plan_output = PlanOutput(
                    summary="Test plan",
                    steps=[
                        PlanStepOutput(id="step-1", description="Test", completed=False)
                    ],
                    created_at=datetime.now(),
                )

                implementation_input = ImplementationInput(
                    plan=plan_output,
                    issue_number=42,
                    issue_title="Test issue",
                    issue_description="Description",
                    issue_labels=[],
                    issue_url="",
                    repo_owner="owner",
                    repo_name="repo",
                    branch_name="test-branch",
                )
                result = await run_implementation_agent(implementation_input)

                # Verify activity returns DTOs
                assert isinstance(result, ImplementationActivityOutput)
                assert len(result.commits) == 1
                assert result.commits[0].sha == expected_commit.sha
                assert result.commits[0].message == expected_commit.message
                assert result.llm_metadata.total_cost_usd == 0.15

    @pytest.mark.asyncio
    async def test_run_implementation_agent_calls_service_with_correct_params(
        self,
    ) -> None:
        """run_implementation_agent calls ImplementationService.implement_changes with correct parameters."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_service_class:
                # Setup mock
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                mock_commit = Commit(
                    sha="sha123",
                    message="Test commit",
                    timestamp=datetime.now(),
                )
                mock_metadata = LLMMetadataOutput(
                    total_cost_usd=0.05,
                    input_tokens=500,
                    output_tokens=250,
                    duration_ms=2000,
                    duration_api_ms=1800,
                    num_turns=1,
                    model="claude-sonnet-4-5-20250929",
                    tools_used=["Skill"],
                    execution_flow="Executed",
                )
                mock_service.implement_changes = AsyncMock(
                    return_value=([mock_commit], mock_metadata)
                )

                # Create test input with DTOs
                plan_output = PlanOutput(
                    summary="Implement auth",
                    steps=[
                        PlanStepOutput(
                            id="step-1", description="Add JWT", completed=False
                        )
                    ],
                    created_at=datetime.now(),
                )

                implementation_input = ImplementationInput(
                    plan=plan_output,
                    issue_number=99,
                    issue_title="Auth feature",
                    issue_description="Add authentication",
                    issue_labels=[],
                    issue_url="",
                    repo_owner="testowner",
                    repo_name="testrepo",
                    branch_name="auth-branch",
                    target_branch="develop",
                )
                await run_implementation_agent(implementation_input)

                # Verify service was called with correct parameters (domain models)
                call_args = mock_service.implement_changes.call_args
                assert call_args.kwargs["repo_owner"] == "testowner"
                assert call_args.kwargs["repo_name"] == "testrepo"
                assert call_args.kwargs["branch_name"] == "auth-branch"
                assert call_args.kwargs["target_branch"] == "develop"
                # Verify domain models were reconstructed
                assert isinstance(call_args.kwargs["plan"], Plan)
                assert isinstance(call_args.kwargs["issue"], Issue)
                assert call_args.kwargs["issue"].number == 99
                assert call_args.kwargs["plan"].summary == "Implement auth"

    @pytest.mark.asyncio
    async def test_run_implementation_agent_preserves_commit_structure(self) -> None:
        """run_implementation_agent preserves all Commit fields."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_service_class:
                # Setup mock
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                # Create detailed commit
                expected_commit = Commit(
                    sha="full-sha-40-chars-1234567890abcdef",
                    message="Implement comprehensive feature with tests",
                    timestamp=datetime(2025, 1, 1, 12, 0, 0),
                    internal_review_feedback=None,
                )
                expected_metadata = LLMMetadataOutput(
                    total_cost_usd=0.25,
                    input_tokens=1500,
                    output_tokens=750,
                    duration_ms=7000,
                    duration_api_ms=6500,
                    num_turns=1,
                    model="claude-sonnet-4-5-20250929",
                    tools_used=["Skill", "Read", "Write", "Edit"],
                    execution_flow="Invoked feature-implementation skill",
                )
                mock_service.implement_changes = AsyncMock(
                    return_value=([expected_commit], expected_metadata)
                )

                # Create test input with DTOs
                plan_output = PlanOutput(
                    summary="Complex plan",
                    steps=[
                        PlanStepOutput(
                            id="step-1", description="Step 1", completed=False
                        )
                    ],
                    created_at=datetime.now(),
                )

                implementation_input = ImplementationInput(
                    plan=plan_output,
                    issue_number=123,
                    issue_title="Complex issue",
                    issue_description="Description",
                    issue_labels=[],
                    issue_url="",
                    repo_owner="owner",
                    repo_name="repo",
                    branch_name="test",
                )
                result = await run_implementation_agent(implementation_input)

                # Verify all fields preserved
                assert result.commits[0].sha == "full-sha-40-chars-1234567890abcdef"
                assert (
                    result.commits[0].message
                    == "Implement comprehensive feature with tests"
                )
                assert result.commits[0].timestamp == datetime(2025, 1, 1, 12, 0, 0)
                assert result.commits[0].internal_review_feedback is None

    @pytest.mark.asyncio
    async def test_run_implementation_agent_passes_config_model_to_claude_client(
        self,
    ) -> None:
        """run_implementation_agent passes config.claude.coding_model to ClaudeClient."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.implementation_activities.ClaudeClient"
            ) as mock_client_class:
                with patch(
                    "troller.worker.activities.implementation_activities.config"
                ) as mock_config:
                    # Setup mock config
                    mock_claude_config = ClaudeModelConfig()
                    mock_claude_config.coding_model = "claude-sonnet-custom"
                    mock_config.claude = mock_claude_config

                    # Setup mock client and service
                    mock_client = MagicMock()
                    mock_client_class.return_value = mock_client

                    with patch(
                        "troller.worker.activities.implementation_activities.ImplementationService"
                    ) as mock_service_class:
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service
                        mock_commit = Commit(
                            sha="test",
                            message="Test",
                            timestamp=datetime.now(),
                        )
                        mock_metadata = LLMMetadataOutput(
                            total_cost_usd=0.01,
                            input_tokens=100,
                            output_tokens=50,
                            duration_ms=1000,
                            duration_api_ms=900,
                            num_turns=1,
                            model="claude-sonnet-custom",
                            tools_used=[],
                            execution_flow="Executed",
                        )
                        mock_service.implement_changes = AsyncMock(
                            return_value=([mock_commit], mock_metadata)
                        )

                        # Create test input with DTOs
                        plan_output = PlanOutput(
                            summary="Test",
                            steps=[],
                            created_at=datetime.now(),
                        )

                        implementation_input = ImplementationInput(
                            plan=plan_output,
                            issue_number=1,
                            issue_title="Test",
                            issue_description="Test",
                            issue_labels=[],
                            issue_url="",
                            repo_owner="test",
                            repo_name="test",
                            branch_name="test",
                        )
                        await run_implementation_agent(implementation_input)

                        # Verify ClaudeClient was created with coding model
                        mock_client_class.assert_called_once_with(
                            model="claude-sonnet-custom"
                        )

    @pytest.mark.asyncio
    async def test_run_implementation_agent_uses_environment_variable_for_model(
        self,
    ) -> None:
        """run_implementation_agent respects CLAUDE_CODING_MODEL environment variable."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "test-key",
                "CLAUDE_CODING_MODEL": "claude-sonnet-from-env",
            },
        ):
            with patch(
                "troller.worker.activities.implementation_activities.ClaudeClient"
            ) as mock_client_class:
                with patch(
                    "troller.worker.activities.implementation_activities.config"
                ) as mock_config:
                    # Setup mock config to reflect environment variable
                    mock_claude_config = ClaudeModelConfig(
                        coding_model="claude-sonnet-from-env"
                    )
                    mock_config.claude = mock_claude_config

                    # Setup mock client and service
                    mock_client = MagicMock()
                    mock_client_class.return_value = mock_client

                    with patch(
                        "troller.worker.activities.implementation_activities.ImplementationService"
                    ) as mock_service_class:
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service
                        mock_commit = Commit(
                            sha="test",
                            message="Test",
                            timestamp=datetime.now(),
                        )
                        mock_metadata = LLMMetadataOutput(
                            total_cost_usd=0.01,
                            input_tokens=100,
                            output_tokens=50,
                            duration_ms=1000,
                            duration_api_ms=900,
                            num_turns=1,
                            model="claude-sonnet-from-env",
                            tools_used=[],
                            execution_flow="Executed",
                        )
                        mock_service.implement_changes = AsyncMock(
                            return_value=([mock_commit], mock_metadata)
                        )

                        # Create test input with DTOs
                        plan_output = PlanOutput(
                            summary="Test",
                            steps=[],
                            created_at=datetime.now(),
                        )

                        implementation_input = ImplementationInput(
                            plan=plan_output,
                            issue_number=1,
                            issue_title="Test",
                            issue_description="Test",
                            issue_labels=[],
                            issue_url="",
                            repo_owner="test",
                            repo_name="test",
                            branch_name="test",
                        )
                        await run_implementation_agent(implementation_input)

                        # Verify ClaudeClient was created with environment model
                        mock_client_class.assert_called_once_with(
                            model="claude-sonnet-from-env"
                        )

    @pytest.mark.asyncio
    async def test_run_implementation_agent_handles_multiple_commits(self) -> None:
        """run_implementation_agent handles multiple commits from service."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.implementation_activities.ImplementationService"
            ) as mock_service_class:
                # Setup mock
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                # Mock multiple commits
                commit1 = Commit(
                    sha="sha1", message="First commit", timestamp=datetime.now()
                )
                commit2 = Commit(
                    sha="sha2", message="Second commit", timestamp=datetime.now()
                )
                metadata = LLMMetadataOutput(
                    total_cost_usd=0.20,
                    input_tokens=1000,
                    output_tokens=500,
                    duration_ms=5000,
                    duration_api_ms=4500,
                    num_turns=1,
                    model="claude-sonnet-4-5-20250929",
                    tools_used=["Skill"],
                    execution_flow="Executed",
                )
                mock_service.implement_changes = AsyncMock(
                    return_value=([commit1, commit2], metadata)
                )

                # Create test input with DTOs
                plan_output = PlanOutput(
                    summary="Test",
                    steps=[
                        PlanStepOutput(id="step-1", description="Test", completed=False)
                    ],
                    created_at=datetime.now(),
                )

                implementation_input = ImplementationInput(
                    plan=plan_output,
                    issue_number=1,
                    issue_title="Test",
                    issue_description="Test",
                    issue_labels=[],
                    issue_url="",
                    repo_owner="owner",
                    repo_name="repo",
                    branch_name="test",
                )
                result = await run_implementation_agent(implementation_input)

                # Verify both commits are returned
                assert len(result.commits) == 2
                assert result.commits[0].sha == "sha1"
                assert result.commits[1].sha == "sha2"

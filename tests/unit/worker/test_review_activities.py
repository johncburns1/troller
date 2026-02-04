"""Unit tests for review activities."""

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from troller.config import ClaudeModelConfig
from troller.domain.models.commit import InternalReviewFeedback
from troller.worker.activities.activity_outputs import (
    CommitOutput,
    InternalReviewFeedbackOutput,
    LLMMetadataOutput,
    PlanOutput,
    PlanStepOutput,
)
from troller.worker.activities.review_activities import (
    ReviewActivityOutput,
    ReviewInput,
    run_review_agent,
)


class TestRunReviewAgent:
    """Test suite for run_review_agent activity."""

    @pytest.mark.asyncio
    async def test_run_review_agent_returns_review_feedback(self) -> None:
        """run_review_agent returns ReviewActivityOutput with feedback."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_service_class:
                # Setup mock
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                # Mock feedback and metadata (domain models from service)
                expected_feedback = InternalReviewFeedback(
                    approved=True,
                    comments=["Code looks good"],
                    suggested_changes=[],
                    timestamp=datetime.now(),
                )
                expected_metadata = LLMMetadataOutput(
                    total_cost_usd=0.05,
                    input_tokens=500,
                    output_tokens=200,
                    duration_ms=3000,
                    duration_api_ms=2800,
                    num_turns=1,
                    model="claude-sonnet-4-5-20250929",
                    tools_used=[],
                    execution_flow="Structured review query",
                )
                mock_service.review_changes = AsyncMock(
                    return_value=(expected_feedback, expected_metadata)
                )

                # Create test input with DTOs
                commits = [
                    CommitOutput(
                        sha="abc123",
                        message="Implement feature",
                        timestamp=datetime.now(),
                    )
                ]
                plan_output = PlanOutput(
                    summary="Test plan",
                    steps=[
                        PlanStepOutput(id="step-1", description="Test", completed=True)
                    ],
                    created_at=datetime.now(),
                )

                review_input = ReviewInput(
                    commits=commits,
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
                result = await run_review_agent(review_input)

                # Verify activity returns DTOs
                assert isinstance(result, ReviewActivityOutput)
                assert isinstance(result.feedback, InternalReviewFeedbackOutput)
                assert result.feedback.approved is True
                assert result.feedback.comments == ["Code looks good"]

    @pytest.mark.asyncio
    async def test_run_review_agent_calls_service_with_correct_params(self) -> None:
        """run_review_agent calls ReviewService.review_changes with correct parameters."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_service_class:
                # Setup mock
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                mock_feedback = InternalReviewFeedback(
                    approved=True,
                    comments=[],
                    suggested_changes=[],
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
                    tools_used=[],
                    execution_flow="Executed",
                )
                mock_service.review_changes = AsyncMock(
                    return_value=(mock_feedback, mock_metadata)
                )

                # Create test input with DTOs
                commits = [
                    CommitOutput(
                        sha="def456",
                        message="Add auth",
                        timestamp=datetime.now(),
                    )
                ]
                plan_output = PlanOutput(
                    summary="Implement auth",
                    steps=[
                        PlanStepOutput(
                            id="step-1", description="Add JWT", completed=True
                        )
                    ],
                    created_at=datetime.now(),
                )

                review_input = ReviewInput(
                    commits=commits,
                    plan=plan_output,
                    issue_number=99,
                    issue_title="Auth feature",
                    issue_description="Add authentication",
                    issue_labels=[],
                    issue_url="",
                    repo_owner="testowner",
                    repo_name="testrepo",
                    branch_name="auth-branch",
                )
                await run_review_agent(review_input)

                # Verify service was called with correct parameters
                call_args = mock_service.review_changes.call_args
                assert call_args.kwargs["repo_owner"] == "testowner"
                assert call_args.kwargs["repo_name"] == "testrepo"
                assert call_args.kwargs["branch_name"] == "auth-branch"
                # Verify domain models were reconstructed
                assert len(call_args.kwargs["commits"]) == 1
                assert call_args.kwargs["commits"][0].sha == "def456"
                assert call_args.kwargs["issue"].number == 99

    @pytest.mark.asyncio
    async def test_run_review_agent_passes_config_model_to_service(self) -> None:
        """run_review_agent passes config.claude.review_model to ReviewService."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.review_activities.ClaudeClient"
            ) as mock_client_class:
                with patch(
                    "troller.worker.activities.review_activities.config"
                ) as mock_config:
                    # Setup mock config
                    mock_claude_config = ClaudeModelConfig()
                    mock_claude_config.review_model = "claude-sonnet-custom"
                    mock_config.claude = mock_claude_config

                    # Setup mock client
                    mock_client = MagicMock()
                    mock_client_class.return_value = mock_client

                    with patch(
                        "troller.worker.activities.review_activities.ReviewService"
                    ) as mock_service_class:
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service
                        mock_feedback = InternalReviewFeedback(
                            approved=True,
                            comments=[],
                            suggested_changes=[],
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
                        mock_service.review_changes = AsyncMock(
                            return_value=(mock_feedback, mock_metadata)
                        )

                        # Create test input with DTOs
                        commits = [
                            CommitOutput(
                                sha="test",
                                message="Test",
                                timestamp=datetime.now(),
                            )
                        ]
                        plan_output = PlanOutput(
                            summary="Test",
                            steps=[],
                            created_at=datetime.now(),
                        )

                        review_input = ReviewInput(
                            commits=commits,
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
                        await run_review_agent(review_input)

                        # Verify ReviewService was created with review model
                        call_args = mock_service_class.call_args
                        assert call_args.kwargs["model"] == "claude-sonnet-custom"

    @pytest.mark.asyncio
    async def test_run_review_agent_returns_rejected_feedback_with_changes(
        self,
    ) -> None:
        """run_review_agent returns feedback with suggested changes when rejected."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_service_class:
                # Setup mock
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                # Mock rejected feedback with suggested changes
                expected_feedback = InternalReviewFeedback(
                    approved=False,
                    comments=["Missing tests", "Code style issues"],
                    suggested_changes=[
                        "Add unit tests for edge cases",
                        "Fix formatting issues",
                    ],
                    timestamp=datetime.now(),
                )
                expected_metadata = LLMMetadataOutput(
                    total_cost_usd=0.05,
                    input_tokens=600,
                    output_tokens=300,
                    duration_ms=3500,
                    duration_api_ms=3200,
                    num_turns=1,
                    model="claude-sonnet-4-5-20250929",
                    tools_used=[],
                    execution_flow="Structured review query",
                )
                mock_service.review_changes = AsyncMock(
                    return_value=(expected_feedback, expected_metadata)
                )

                # Create test input with DTOs
                commits = [
                    CommitOutput(
                        sha="abc123",
                        message="Implement feature",
                        timestamp=datetime.now(),
                    )
                ]
                plan_output = PlanOutput(
                    summary="Test plan",
                    steps=[
                        PlanStepOutput(id="step-1", description="Test", completed=True)
                    ],
                    created_at=datetime.now(),
                )

                review_input = ReviewInput(
                    commits=commits,
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
                result = await run_review_agent(review_input)

                # Verify rejected feedback structure
                assert result.feedback.approved is False
                assert "Missing tests" in result.feedback.comments
                assert (
                    "Add unit tests for edge cases" in result.feedback.suggested_changes
                )

    @pytest.mark.asyncio
    async def test_run_review_agent_preserves_feedback_timestamp(self) -> None:
        """run_review_agent preserves feedback timestamp."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_service_class:
                # Setup mock
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                # Create specific timestamp
                specific_time = datetime(2025, 1, 15, 12, 30, 0)
                mock_feedback = InternalReviewFeedback(
                    approved=True,
                    comments=[],
                    suggested_changes=[],
                    timestamp=specific_time,
                )
                mock_metadata = LLMMetadataOutput(
                    total_cost_usd=0.05,
                    input_tokens=500,
                    output_tokens=200,
                    duration_ms=2000,
                    duration_api_ms=1800,
                    num_turns=1,
                    model="claude-sonnet-4-5-20250929",
                    tools_used=[],
                    execution_flow="Structured review query",
                )
                mock_service.review_changes = AsyncMock(
                    return_value=(mock_feedback, mock_metadata)
                )

                # Create test input
                commits = [
                    CommitOutput(
                        sha="abc123",
                        message="Test",
                        timestamp=datetime.now(),
                    )
                ]
                plan_output = PlanOutput(
                    summary="Test",
                    steps=[],
                    created_at=datetime.now(),
                )

                review_input = ReviewInput(
                    commits=commits,
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
                result = await run_review_agent(review_input)

                # Verify timestamp is preserved
                assert result.feedback.timestamp == specific_time

    @pytest.mark.asyncio
    async def test_run_review_agent_returns_llm_metadata(self) -> None:
        """run_review_agent returns LLM metadata for cost tracking."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.activities.review_activities.ReviewService"
            ) as mock_service_class:
                # Setup mock
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service

                mock_feedback = InternalReviewFeedback(
                    approved=True,
                    comments=[],
                    suggested_changes=[],
                    timestamp=datetime.now(),
                )
                mock_metadata = LLMMetadataOutput(
                    total_cost_usd=0.12,
                    input_tokens=800,
                    output_tokens=400,
                    duration_ms=4000,
                    duration_api_ms=3800,
                    num_turns=1,
                    model="claude-sonnet-4-5-20250929",
                    tools_used=[],
                    execution_flow="Structured review query",
                )
                mock_service.review_changes = AsyncMock(
                    return_value=(mock_feedback, mock_metadata)
                )

                # Create test input
                commits = [
                    CommitOutput(
                        sha="abc123",
                        message="Test",
                        timestamp=datetime.now(),
                    )
                ]
                plan_output = PlanOutput(
                    summary="Test",
                    steps=[],
                    created_at=datetime.now(),
                )

                review_input = ReviewInput(
                    commits=commits,
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
                result = await run_review_agent(review_input)

                # Verify metadata
                assert result.llm_metadata.total_cost_usd == 0.12
                assert result.llm_metadata.input_tokens == 800
                assert result.llm_metadata.duration_ms == 4000

"""Unit tests for Claude API client adapter."""

import os
from unittest.mock import MagicMock, patch

import pytest

from troller.domain.models.plan import Plan
from troller.worker.adapters.claude_client import ClaudeClient


class TestClaudeClient:
    """Test suite for ClaudeClient adapter."""

    def test_init_reads_api_key_from_env(self) -> None:
        """ClaudeClient reads ANTHROPIC_API_KEY from environment."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.Anthropic"
            ) as mock_anthropic:
                _client = ClaudeClient()

                # Verify Anthropic was instantiated with API key
                mock_anthropic.assert_called_once_with(api_key="test-key")

    def test_init_raises_error_when_api_key_missing(self) -> None:
        """ClaudeClient raises clear error when ANTHROPIC_API_KEY is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="ANTHROPIC_API_KEY environment variable is required"
            ):
                ClaudeClient()

    def test_generate_plan_returns_plan_object(self) -> None:
        """generate_plan returns Plan domain object."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.Anthropic"
            ) as mock_anthropic_class:
                # Setup mock
                mock_anthropic = MagicMock()
                mock_anthropic_class.return_value = mock_anthropic

                # Mock the response
                mock_response = MagicMock()
                mock_response.content = [
                    MagicMock(
                        type="tool_use",
                        input={
                            "summary": "Test plan summary",
                            "steps": [
                                {
                                    "id": "step-1",
                                    "description": "First step",
                                    "completed": False,
                                    "related_files": ["file.py"],
                                    "estimated_complexity": "simple",
                                }
                            ],
                            "technical_approach": "Test approach",
                            "testing_strategy": "Test strategy",
                        },
                    )
                ]
                mock_anthropic.messages.create.return_value = mock_response

                # Test
                client = ClaudeClient()
                plan = client.generate_plan(
                    issue_title="Test Issue", issue_body="Test body", issue_number=123
                )

                # Verify
                assert isinstance(plan, Plan)
                assert plan.summary == "Test plan summary"
                assert len(plan.steps) == 1
                assert plan.steps[0].id == "step-1"
                assert plan.technical_approach == "Test approach"
                assert plan.testing_strategy == "Test strategy"

    def test_generate_plan_uses_claude_opus_model(self) -> None:
        """generate_plan uses Claude Opus 4.5 model."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.Anthropic"
            ) as mock_anthropic_class:
                mock_anthropic = MagicMock()
                mock_anthropic_class.return_value = mock_anthropic

                mock_response = MagicMock()
                mock_response.content = [
                    MagicMock(
                        type="tool_use",
                        input={
                            "summary": "Test",
                            "steps": [],
                            "technical_approach": None,
                            "testing_strategy": None,
                        },
                    )
                ]
                mock_anthropic.messages.create.return_value = mock_response

                client = ClaudeClient()
                client.generate_plan(
                    issue_title="Test", issue_body="Body", issue_number=1
                )

                # Verify model parameter
                call_args = mock_anthropic.messages.create.call_args
                assert call_args.kwargs["model"] == "claude-opus-4-5-20251101"

    def test_generate_plan_includes_issue_context_in_prompt(self) -> None:
        """generate_plan includes issue details in the prompt."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.Anthropic"
            ) as mock_anthropic_class:
                mock_anthropic = MagicMock()
                mock_anthropic_class.return_value = mock_anthropic

                mock_response = MagicMock()
                mock_response.content = [
                    MagicMock(
                        type="tool_use",
                        input={
                            "summary": "Test",
                            "steps": [],
                            "technical_approach": None,
                            "testing_strategy": None,
                        },
                    )
                ]
                mock_anthropic.messages.create.return_value = mock_response

                client = ClaudeClient()
                client.generate_plan(
                    issue_title="Add feature X",
                    issue_body="Implement feature X with Y",
                    issue_number=42,
                )

                # Verify issue details in messages
                call_args = mock_anthropic.messages.create.call_args
                messages = call_args.kwargs["messages"]
                user_message = messages[0]["content"]

                assert "Add feature X" in user_message
                assert "Implement feature X with Y" in user_message
                assert "42" in user_message

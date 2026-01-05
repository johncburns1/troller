"""Unit tests for Claude API client adapter."""

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from troller.domain.models.plan import Plan
from troller.worker.adapters.claude_client import ClaudeClient


class TestClaudeClient:
    """Test suite for ClaudeClient adapter."""

    def test_init_stores_api_key_from_env(self) -> None:
        """ClaudeClient reads and stores ANTHROPIC_API_KEY from environment."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            client = ClaudeClient()
            assert client._api_key == "test-key"
            assert client._anthropic_client is not None

    def test_init_raises_error_when_api_key_missing(self) -> None:
        """ClaudeClient raises clear error when ANTHROPIC_API_KEY is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="ANTHROPIC_API_KEY environment variable is required"
            ):
                ClaudeClient()

    @pytest.mark.asyncio
    async def test_generate_plan_clones_repository(self) -> None:
        """generate_plan clones the target repository."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.subprocess.run"
            ) as mock_run:
                with patch("troller.worker.adapters.claude_client.query") as mock_query:
                    with patch(
                        "troller.worker.adapters.claude_client.Anthropic"
                    ) as mock_anthropic_class:
                        with patch(
                            "troller.worker.adapters.claude_client.shutil.rmtree"
                        ):
                            # Mock successful git clone
                            mock_run.return_value = MagicMock(returncode=0)

                            # Mock agent SDK exploration phase
                            async def mock_query_response(*args, **kwargs):
                                yield MagicMock(
                                    result="Architecture: hexagonal pattern"
                                )

                            mock_query.side_effect = mock_query_response

                            # Mock Anthropic client for planning phase
                            mock_anthropic = MagicMock()
                            mock_anthropic_class.return_value = mock_anthropic
                            mock_response = MagicMock()
                            mock_response.content = [
                                MagicMock(
                                    text='{"summary": "Test", "steps": [], "technical_approach": null, "testing_strategy": null}'
                                )
                            ]
                            mock_anthropic.messages.create.return_value = mock_response

                            client = ClaudeClient()
                            await client.generate_plan(
                                issue_title="Test",
                                issue_body="Body",
                                issue_number=1,
                                repo_owner="testowner",
                                repo_name="testrepo",
                            )

                            # Verify git clone was called
                            assert mock_run.called
                            clone_call = mock_run.call_args_list[0]
                            assert "git" in clone_call[0][0]
                            assert "clone" in clone_call[0][0]
                            assert (
                                "https://github.com/testowner/testrepo.git"
                                in clone_call[0][0]
                            )

    @pytest.mark.asyncio
    async def test_generate_plan_cleans_up_repository(self) -> None:
        """generate_plan removes cloned repository after completion."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.subprocess.run"
            ) as mock_run:
                with patch("troller.worker.adapters.claude_client.query") as mock_query:
                    with patch(
                        "troller.worker.adapters.claude_client.Anthropic"
                    ) as mock_anthropic_class:
                        with patch(
                            "troller.worker.adapters.claude_client.shutil.rmtree"
                        ) as mock_rmtree:
                            mock_run.return_value = MagicMock(returncode=0)

                            async def mock_query_response(*args, **kwargs):
                                yield MagicMock(result="Architecture found")

                            # Mock Anthropic client for planning phase
                            mock_anthropic = MagicMock()
                            mock_anthropic_class.return_value = mock_anthropic
                            mock_response = MagicMock()
                            mock_response.content = [
                                MagicMock(
                                    text='{"summary": "Test", "steps": [], "technical_approach": null, "testing_strategy": null}'
                                )
                            ]
                            mock_anthropic.messages.create.return_value = mock_response

                            mock_query.side_effect = mock_query_response

                            client = ClaudeClient()
                            await client.generate_plan(
                                issue_title="Test",
                                issue_body="Body",
                                issue_number=1,
                                repo_owner="owner",
                                repo_name="repo",
                            )

                            # Verify cleanup was called
                            assert mock_rmtree.called

    @pytest.mark.asyncio
    async def test_generate_plan_cleans_up_on_failure(self) -> None:
        """generate_plan removes cloned repository even if planning fails."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.subprocess.run"
            ) as mock_run:
                with patch("troller.worker.adapters.claude_client.query") as mock_query:
                    with patch(
                        "troller.worker.adapters.claude_client.Anthropic"
                    ) as mock_anthropic_class:
                        with patch(
                            "troller.worker.adapters.claude_client.shutil.rmtree"
                        ) as mock_rmtree:
                            # Successful clone
                            mock_run.return_value = MagicMock(returncode=0)

                            # Agent query fails
                            async def failing_query(*args, **kwargs):
                                raise RuntimeError("Agent failed")
                                yield  # Make it async generator

                            mock_query.side_effect = failing_query

                            # Mock Anthropic (won't be reached due to failure)
                            mock_anthropic = MagicMock()
                            mock_anthropic_class.return_value = mock_anthropic

                            client = ClaudeClient()

                            with pytest.raises(RuntimeError, match="Agent failed"):
                                await client.generate_plan(
                                    issue_title="Test",
                                    issue_body="Body",
                                    issue_number=1,
                                    repo_owner="owner",
                                    repo_name="repo",
                                )

                            # Verify cleanup still happened
                            assert mock_rmtree.called

    @pytest.mark.asyncio
    async def test_generate_plan_returns_plan_with_codebase_context(self) -> None:
        """generate_plan returns Plan with codebase analysis in metadata."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.subprocess.run"
            ) as mock_run:
                with patch("troller.worker.adapters.claude_client.query") as mock_query:
                    with patch(
                        "troller.worker.adapters.claude_client.Anthropic"
                    ) as mock_anthropic_class:
                        with patch(
                            "troller.worker.adapters.claude_client.shutil.rmtree"
                        ):
                            mock_run.return_value = MagicMock(returncode=0)

                            async def mock_query_response(*args, **kwargs):
                                yield MagicMock(result="Hexagonal architecture found")

                            # Mock Anthropic client for planning phase
                            mock_anthropic = MagicMock()
                            mock_anthropic_class.return_value = mock_anthropic
                            mock_response = MagicMock()
                            mock_response.content = [
                                MagicMock(
                                    text='{"summary": "Implement feature", "steps": [{"id": "step-1", "description": "Add handler", "completed": false, "related_files": ["handler.py"], "estimated_complexity": "moderate"}], "technical_approach": "Use existing patterns", "testing_strategy": "Unit tests"}'
                                )
                            ]
                            mock_anthropic.messages.create.return_value = mock_response

                            mock_query.side_effect = mock_query_response

                            client = ClaudeClient()
                            plan = await client.generate_plan(
                                issue_title="Add feature",
                                issue_body="New feature needed",
                                issue_number=42,
                                repo_owner="owner",
                                repo_name="repo",
                            )

                            # Verify plan structure
                            assert isinstance(plan, Plan)
                            assert plan.summary == "Implement feature"
                            assert len(plan.steps) == 1
                            assert plan.steps[0].id == "step-1"
                            assert plan.steps[0].related_files == ["handler.py"]
                            assert plan.metadata["issue_number"] == 42
                            assert "codebase_analysis" in plan.metadata
                            assert (
                                "Hexagonal architecture"
                                in plan.metadata["codebase_analysis"]
                            )

    @pytest.mark.asyncio
    async def test_generate_plan_uses_agent_sdk_with_correct_options(self) -> None:
        """generate_plan configures Agent SDK with correct working directory and tools."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.subprocess.run"
            ) as mock_run:
                with patch("troller.worker.adapters.claude_client.query") as mock_query:
                    with patch(
                        "troller.worker.adapters.claude_client.Anthropic"
                    ) as mock_anthropic_class:
                        with patch(
                            "troller.worker.adapters.claude_client.shutil.rmtree"
                        ):
                            mock_run.return_value = MagicMock(returncode=0)

                            captured_options = []

                            async def capture_options(*args, **kwargs):
                                captured_options.append(kwargs.get("options"))
                                yield MagicMock(result="Analysis")

                            mock_query.side_effect = capture_options

                            # Mock Anthropic client for planning phase
                            mock_anthropic = MagicMock()
                            mock_anthropic_class.return_value = mock_anthropic
                            mock_response = MagicMock()
                            mock_response.content = [
                                MagicMock(
                                    text='{"summary": "Test", "steps": [], "technical_approach": null, "testing_strategy": null}'
                                )
                            ]
                            mock_anthropic.messages.create.return_value = mock_response

                            client = ClaudeClient()
                            await client.generate_plan(
                                issue_title="Test",
                                issue_body="Body",
                                issue_number=1,
                                repo_owner="owner",
                                repo_name="repo",
                            )

                            # Verify agent options
                            assert len(captured_options) >= 1
                            options = captured_options[0]
                            assert options is not None
                            assert "Read" in options.allowed_tools
                            assert "Glob" in options.allowed_tools
                            assert "Grep" in options.allowed_tools
                            assert options.permission_mode == "bypassPermissions"

    @pytest.mark.asyncio
    async def test_generate_plan_tries_master_if_main_fails(self) -> None:
        """generate_plan tries master branch if main branch doesn't exist."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.subprocess.run"
            ) as mock_run:
                with patch("troller.worker.adapters.claude_client.query") as mock_query:
                    with patch(
                        "troller.worker.adapters.claude_client.Anthropic"
                    ) as mock_anthropic_class:
                        with patch(
                            "troller.worker.adapters.claude_client.shutil.rmtree"
                        ):
                            # First call (main branch) raises exception, second call (master) succeeds
                            def run_side_effect(*args, **kwargs):
                                """Mock subprocess.run to fail on main, succeed on master."""
                                if "main" in args[0]:
                                    raise subprocess.CalledProcessError(
                                        1, "git", stderr="branch not found"
                                    )
                                # master branch succeeds
                                return MagicMock(returncode=0)

                            mock_run.side_effect = run_side_effect

                            async def mock_query_response(*args, **kwargs):
                                yield MagicMock(result="Analysis")

                            mock_query.side_effect = mock_query_response

                            # Mock Anthropic client for planning phase
                            mock_anthropic = MagicMock()
                            mock_anthropic_class.return_value = mock_anthropic
                            mock_response = MagicMock()
                            mock_response.content = [
                                MagicMock(
                                    text='{"summary": "Test", "steps": [], "technical_approach": null, "testing_strategy": null}'
                                )
                            ]
                            mock_anthropic.messages.create.return_value = mock_response

                            client = ClaudeClient()
                            # This should not raise an error
                            plan = await client.generate_plan(
                                issue_title="Test",
                                issue_body="Body",
                                issue_number=1,
                                repo_owner="owner",
                                repo_name="repo",
                            )

                            # Verify both main and master were tried
                            assert mock_run.call_count == 2
                            assert isinstance(plan, Plan)

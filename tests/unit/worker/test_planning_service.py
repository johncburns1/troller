"""Unit tests for Planning service."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from troller.domain.models.plan import Plan
from troller.worker.adapters.claude_client import ClaudeClient
from troller.worker.adapters.repo_cloner import RepoCloner
from troller.worker.services.planning_service import PlanningService


class MockAssistantMessage:
    """Mock AssistantMessage with text content."""

    def __init__(self, text: str):
        self.content = [MockTextBlock(text)]


class MockTextBlock:
    """Mock TextBlock with text."""

    def __init__(self, text: str):
        self.text = text


class MockToolUseBlock:
    """Mock ToolUseBlock for TodoWrite."""

    def __init__(self, name: str, input_data: dict):
        self.name = name
        self.input = input_data


class TestPlanningService:
    """Test suite for PlanningService."""

    @pytest.mark.asyncio
    async def test_generate_plan_clones_repository(self) -> None:
        """generate_plan clones the target repository."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"))
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client with skill-based response
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MockAssistantMessage("Plan created successfully")

        mock_client.query = mock_query_response

        service = PlanningService(mock_client, mock_cloner)
        await service.generate_plan(
            issue_title="Test",
            issue_body="Body",
            issue_number=1,
            repo_owner="testowner",
            repo_name="testrepo",
        )

        # Verify clone_to_temp was called
        mock_cloner.clone_to_temp.assert_called_once_with("testowner", "testrepo", None)

    @pytest.mark.asyncio
    async def test_generate_plan_cleans_up_repository(self) -> None:
        """generate_plan removes cloned repository after completion."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        temp_dir = MagicMock(spec=Path)
        temp_dir.exists.return_value = True
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(temp_dir, Path("/tmp/test/repo"))
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MockAssistantMessage("Plan complete")

        mock_client.query = mock_query_response

        service = PlanningService(mock_client, mock_cloner)
        await service.generate_plan(
            issue_title="Test",
            issue_body="Body",
            issue_number=1,
            repo_owner="owner",
            repo_name="repo",
        )

        # Verify cleanup was called
        mock_cloner.cleanup.assert_called_once_with(temp_dir)

    @pytest.mark.asyncio
    async def test_generate_plan_cleans_up_on_failure(self) -> None:
        """generate_plan removes cloned repository even if planning fails."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        temp_dir = MagicMock(spec=Path)
        temp_dir.exists.return_value = True
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(temp_dir, Path("/tmp/test/repo"))
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client with failing query
        mock_client = MagicMock(spec=ClaudeClient)

        async def failing_query(*args, **kwargs):
            raise RuntimeError("Agent failed")
            yield  # Make it async generator (but never reached)

        mock_client.query = failing_query

        service = PlanningService(mock_client, mock_cloner)

        with pytest.raises(RuntimeError, match="Agent failed"):
            await service.generate_plan(
                issue_title="Test",
                issue_body="Body",
                issue_number=1,
                repo_owner="owner",
                repo_name="repo",
            )

        # Verify cleanup still happened
        mock_cloner.cleanup.assert_called_once_with(temp_dir)

    @pytest.mark.asyncio
    async def test_generate_plan_enables_skill_tool(self) -> None:
        """generate_plan enables Skill tool to invoke feature-planner."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"))
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture options
        mock_client = MagicMock(spec=ClaudeClient)
        captured_options = []

        async def capture_options(prompt, options):
            captured_options.append(options)
            yield MockAssistantMessage("Plan generated")

        mock_client.query = capture_options

        service = PlanningService(mock_client, mock_cloner)
        await service.generate_plan(
            issue_title="Test",
            issue_body="Body",
            issue_number=1,
            repo_owner="owner",
            repo_name="repo",
        )

        # Verify Skill tool is enabled
        assert len(captured_options) > 0
        options = captured_options[0]
        assert "Skill" in options.allowed_tools

    @pytest.mark.asyncio
    async def test_generate_plan_loads_global_and_project_skills(self) -> None:
        """generate_plan loads skills from user and project settings."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"))
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture options
        mock_client = MagicMock(spec=ClaudeClient)
        captured_options = []

        async def capture_options(prompt, options):
            captured_options.append(options)
            yield MockAssistantMessage("Plan created")

        mock_client.query = capture_options

        service = PlanningService(mock_client, mock_cloner)
        await service.generate_plan(
            issue_title="Test",
            issue_body="Body",
            issue_number=1,
            repo_owner="owner",
            repo_name="repo",
        )

        # Verify setting_sources includes user and project
        assert len(captured_options) > 0
        options = captured_options[0]
        assert "user" in options.setting_sources
        assert "project" in options.setting_sources

    @pytest.mark.asyncio
    async def test_generate_plan_invokes_single_query(self) -> None:
        """generate_plan uses single query() call instead of multi-phase approach."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"))
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to count query calls
        mock_client = MagicMock(spec=ClaudeClient)
        query_call_count = [0]

        async def count_query_calls(prompt, options):
            query_call_count[0] += 1
            yield MockAssistantMessage("Plan complete")

        mock_client.query = count_query_calls

        service = PlanningService(mock_client, mock_cloner)
        await service.generate_plan(
            issue_title="Test",
            issue_body="Body",
            issue_number=1,
            repo_owner="owner",
            repo_name="repo",
        )

        # Verify only one query call (not multi-phase)
        assert query_call_count[0] == 1

    @pytest.mark.asyncio
    async def test_generate_plan_returns_plan_with_metadata(self) -> None:
        """generate_plan returns Plan with issue number in metadata."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"))
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client with realistic response
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            # Simulate assistant response with plan text
            yield MockAssistantMessage(
                "## Implementation Plan\n\nAdd new feature X to the system."
            )

        mock_client.query = mock_query_response

        service = PlanningService(mock_client, mock_cloner)
        plan = await service.generate_plan(
            issue_title="Add feature",
            issue_body="New feature needed",
            issue_number=42,
            repo_owner="owner",
            repo_name="repo",
        )

        # Verify plan structure
        assert isinstance(plan, Plan)
        assert plan.metadata["issue_number"] == 42

    @pytest.mark.asyncio
    async def test_generate_plan_passes_issue_to_prompt(self) -> None:
        """generate_plan includes issue title and body in query prompt."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"))
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture prompt
        mock_client = MagicMock(spec=ClaudeClient)
        captured_prompts = []

        async def capture_prompt(prompt, options):
            captured_prompts.append(prompt)
            yield MockAssistantMessage("Plan complete")

        mock_client.query = capture_prompt

        service = PlanningService(mock_client, mock_cloner)
        await service.generate_plan(
            issue_title="Add authentication",
            issue_body="Implement JWT auth",
            issue_number=1,
            repo_owner="owner",
            repo_name="repo",
        )

        # Verify prompt includes issue details
        assert len(captured_prompts) > 0
        prompt = captured_prompts[0]
        assert "Add authentication" in prompt
        assert "Implement JWT auth" in prompt

    @pytest.mark.asyncio
    async def test_generate_plan_passes_target_branch_to_cloner(self) -> None:
        """generate_plan passes target_branch parameter to RepoCloner."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"))
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MockAssistantMessage("Analysis")

        mock_client.query = mock_query_response

        service = PlanningService(mock_client, mock_cloner)
        await service.generate_plan(
            issue_title="Test",
            issue_body="Body",
            issue_number=1,
            repo_owner="owner",
            repo_name="repo",
            target_branch="develop",
        )

        # Verify clone_to_temp was called with target_branch
        mock_cloner.clone_to_temp.assert_called_once_with("owner", "repo", "develop")

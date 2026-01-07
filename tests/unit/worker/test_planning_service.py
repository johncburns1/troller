"""Unit tests for Planning service."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from troller.domain.models.plan import Plan
from troller.worker.adapters.claude_client import ClaudeClient
from troller.worker.adapters.repo_cloner import RepoCloner
from troller.worker.services.planning_service import PlanningService


class MockStructuredOutputMessage:
    """Mock message with structured_output attribute."""

    def __init__(self, structured_output: dict | None = None):
        self.structured_output = structured_output


def create_mock_plan_response() -> dict:
    """Create a mock PlanResponse-like dictionary for testing."""
    return {
        "summary": "Implement feature X with proper testing",
        "steps": [
            {
                "id": "step-1",
                "description": "Create domain model",
                "completed": False,
                "related_files": ["src/domain/models/feature.py"],
                "estimated_complexity": "simple",
            },
            {
                "id": "step-2",
                "description": "Implement service layer",
                "completed": False,
                "related_files": ["src/services/feature_service.py"],
                "estimated_complexity": "moderate",
            },
        ],
        "technical_approach": "Use hexagonal architecture with domain-driven design",
        "testing_strategy": "Unit tests for domain logic, integration tests for workflows",
    }


class TestPlanningService:
    """Test suite for PlanningService."""

    @pytest.mark.asyncio
    async def test_generate_plan_clones_repository(self) -> None:
        """generate_plan clones the target repository."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client with structured output response
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MockStructuredOutputMessage(create_mock_plan_response())

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
            return_value=(temp_dir, Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client with structured output
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MockStructuredOutputMessage(create_mock_plan_response())

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
            return_value=(temp_dir, Path("/tmp/test/repo"), "abc123")
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
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture options
        mock_client = MagicMock(spec=ClaudeClient)
        captured_options = []

        async def capture_options(prompt, options):
            captured_options.append(options)
            yield MockStructuredOutputMessage(create_mock_plan_response())

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
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture options
        mock_client = MagicMock(spec=ClaudeClient)
        captured_options = []

        async def capture_options(prompt, options):
            captured_options.append(options)
            yield MockStructuredOutputMessage(create_mock_plan_response())

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
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to count query calls
        mock_client = MagicMock(spec=ClaudeClient)
        query_call_count = [0]

        async def count_query_calls(prompt, options):
            query_call_count[0] += 1
            yield MockStructuredOutputMessage(create_mock_plan_response())

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
        """generate_plan returns Plan with issue number and structured data as first-class attributes."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client with structured output
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MockStructuredOutputMessage(create_mock_plan_response())

        mock_client.query = mock_query_response

        service = PlanningService(mock_client, mock_cloner)
        plan = await service.generate_plan(
            issue_title="Add feature",
            issue_body="New feature needed",
            issue_number=42,
            repo_owner="owner",
            repo_name="repo",
        )

        # Verify plan structure with first-class attributes
        assert isinstance(plan, Plan)
        assert plan.metadata["issue_number"] == 42
        assert (
            plan.technical_approach
            == "Use hexagonal architecture with domain-driven design"
        )
        assert (
            plan.testing_strategy
            == "Unit tests for domain logic, integration tests for workflows"
        )

        # Verify steps have first-class attributes too
        assert len(plan.steps) == 2
        assert plan.steps[0].related_files == ["src/domain/models/feature.py"]
        assert plan.steps[0].estimated_complexity == "simple"
        assert plan.steps[1].related_files == ["src/services/feature_service.py"]
        assert plan.steps[1].estimated_complexity == "moderate"

    @pytest.mark.asyncio
    async def test_generate_plan_passes_issue_to_prompt(self) -> None:
        """generate_plan includes issue title and body in query prompt."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture prompt
        mock_client = MagicMock(spec=ClaudeClient)
        captured_prompts = []

        async def capture_prompt(prompt, options):
            captured_prompts.append(prompt)
            yield MockStructuredOutputMessage(create_mock_plan_response())

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
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client with structured output
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MockStructuredOutputMessage(create_mock_plan_response())

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

    @pytest.mark.asyncio
    async def test_generate_plan_configures_structured_outputs(self) -> None:
        """generate_plan configures output_format with PlanResponse schema."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client to capture options
        mock_client = MagicMock(spec=ClaudeClient)
        captured_options = []

        async def capture_options(prompt, options):
            captured_options.append(options)
            yield MockStructuredOutputMessage(create_mock_plan_response())

        mock_client.query = capture_options

        service = PlanningService(mock_client, mock_cloner)
        await service.generate_plan(
            issue_title="Test",
            issue_body="Body",
            issue_number=1,
            repo_owner="owner",
            repo_name="repo",
        )

        # Verify output_format is configured with json_schema
        assert len(captured_options) > 0
        options = captured_options[0]
        assert "output_format" in options.__dict__
        assert options.output_format["type"] == "json_schema"
        assert "schema" in options.output_format

    @pytest.mark.asyncio
    async def test_generate_plan_raises_error_when_no_structured_output(self) -> None:
        """generate_plan raises RuntimeError when agent doesn't return structured output."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), "abc123")
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client that returns message without structured_output
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MockStructuredOutputMessage(None)

        mock_client.query = mock_query_response

        service = PlanningService(mock_client, mock_cloner)

        with pytest.raises(
            RuntimeError, match="Planning agent did not return structured output"
        ):
            await service.generate_plan(
                issue_title="Test",
                issue_body="Body",
                issue_number=1,
                repo_owner="owner",
                repo_name="repo",
            )

    @pytest.mark.asyncio
    async def test_generate_plan_captures_and_stores_commit_hash(self) -> None:
        """generate_plan captures commit hash from RepoCloner and stores in Plan."""
        commit_sha = "abc123def456789012345678901234567890abcd"

        # Mock RepoCloner to return commit hash
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"), commit_sha)
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client with structured output
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MockStructuredOutputMessage(create_mock_plan_response())

        mock_client.query = mock_query_response

        service = PlanningService(mock_client, mock_cloner)
        plan = await service.generate_plan(
            issue_title="Test feature",
            issue_body="Implement test",
            issue_number=27,
            repo_owner="owner",
            repo_name="repo",
        )

        # Verify commit hash is stored in Plan
        assert plan.based_on_commit == commit_sha

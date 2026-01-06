"""Unit tests for Planning service."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from troller.domain.models.plan import Plan
from troller.worker.adapters.claude_client import ClaudeClient
from troller.worker.adapters.repo_cloner import RepoCloner
from troller.worker.services.planning_models import PlanResponse, PlanStepResponse
from troller.worker.services.planning_service import PlanningService


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

        # Mock Claude client
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MagicMock(result="Architecture: hexagonal pattern")

        mock_client.query = mock_query_response

        # Mock structured query
        mock_client.structured_query = AsyncMock(
            return_value=PlanResponse(
                summary="Test",
                steps=[],
                technical_approach=None,
                testing_strategy=None,
            )
        )

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
            yield MagicMock(result="Architecture found")

        mock_client.query = mock_query_response
        mock_client.structured_query = AsyncMock(
            return_value=PlanResponse(
                summary="Test",
                steps=[],
                technical_approach=None,
                testing_strategy=None,
            )
        )

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
    async def test_generate_plan_returns_plan_with_codebase_context(self) -> None:
        """generate_plan returns Plan with codebase analysis in metadata."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"))
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MagicMock(result="Hexagonal architecture found")

        mock_client.query = mock_query_response

        # Mock structured query with plan data
        mock_plan_response = PlanResponse(
            summary="Implement feature",
            steps=[
                PlanStepResponse(
                    id="step-1",
                    description="Add handler",
                    completed=False,
                    related_files=["handler.py"],
                    estimated_complexity="moderate",
                )
            ],
            technical_approach="Use existing patterns",
            testing_strategy="Unit tests",
        )
        mock_client.structured_query = AsyncMock(return_value=mock_plan_response)

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
        assert plan.summary == "Implement feature"
        assert len(plan.steps) == 1
        assert plan.steps[0].id == "step-1"
        assert plan.steps[0].related_files == ["handler.py"]
        assert plan.metadata["issue_number"] == 42
        assert "codebase_analysis" in plan.metadata
        assert "Hexagonal architecture" in plan.metadata["codebase_analysis"]

    @pytest.mark.asyncio
    async def test_generate_plan_uses_client_query_with_correct_options(self) -> None:
        """generate_plan calls client.query() with correct codebase options."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"))
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client
        mock_client = MagicMock(spec=ClaudeClient)

        captured_options = []

        async def capture_options(prompt, options):
            captured_options.append(options)
            yield MagicMock(result="Analysis")

        mock_client.query = capture_options
        mock_client.structured_query = AsyncMock(
            return_value=PlanResponse(
                summary="Test",
                steps=[],
                technical_approach=None,
                testing_strategy=None,
            )
        )

        service = PlanningService(mock_client, mock_cloner)
        await service.generate_plan(
            issue_title="Test",
            issue_body="Body",
            issue_number=1,
            repo_owner="owner",
            repo_name="repo",
        )

        # Verify client.query was called with options
        assert len(captured_options) >= 1
        options = captured_options[0]
        assert options is not None
        assert "Read" in options.allowed_tools
        assert "Glob" in options.allowed_tools
        assert "Grep" in options.allowed_tools
        assert options.permission_mode == "bypassPermissions"

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
            yield MagicMock(result="Analysis")

        mock_client.query = mock_query_response
        mock_client.structured_query = AsyncMock(
            return_value=PlanResponse(
                summary="Test",
                steps=[],
                technical_approach=None,
                testing_strategy=None,
            )
        )

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
    async def test_generate_plan_uses_structured_query_for_plan(self) -> None:
        """generate_plan uses structured_query() for schema-validated plan generation."""
        # Mock RepoCloner
        mock_cloner = MagicMock(spec=RepoCloner)
        mock_cloner.clone_to_temp = AsyncMock(
            return_value=(Path("/tmp/test"), Path("/tmp/test/repo"))
        )
        mock_cloner.cleanup = MagicMock()

        # Mock Claude client
        mock_client = MagicMock(spec=ClaudeClient)

        async def mock_query_response(*args, **kwargs):
            yield MagicMock(result="Codebase analyzed")

        mock_client.query = mock_query_response
        mock_client.structured_query = AsyncMock(
            return_value=PlanResponse(
                summary="Implementation plan",
                steps=[],
                technical_approach=None,
                testing_strategy=None,
            )
        )

        service = PlanningService(mock_client, mock_cloner)
        await service.generate_plan(
            issue_title="Test",
            issue_body="Body",
            issue_number=1,
            repo_owner="owner",
            repo_name="repo",
        )

        # Verify structured_query was called with PlanResponse schema
        assert mock_client.structured_query.called
        call_args = mock_client.structured_query.call_args
        assert call_args[0][1] == PlanResponse  # schema parameter

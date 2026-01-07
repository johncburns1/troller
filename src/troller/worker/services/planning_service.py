"""Planning service for generating codebase-aware implementation plans.

This service orchestrates the plan generation workflow:
1. Clone repository
2. Invoke feature-planner skill via Claude Agent SDK with structured outputs
3. Convert validated PlanResponse to Plan domain model
4. Clean up cloned repository
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions

from troller.domain.models.llm_metadata import LLMMetadata
from troller.domain.models.plan import Plan, PlanStep
from troller.worker.adapters.claude_client import ClaudeClient
from troller.worker.adapters.repo_cloner import RepoCloner
from troller.worker.services.metadata_extractor import MetadataExtractor
from troller.worker.services.planning_models import PlanResponse


class PlanningService:
    """Service for generating codebase-aware implementation plans.

    This service uses ClaudeClient to:
    1. Clone the target repository
    2. Invoke the feature-planner skill via Agent SDK
    3. Parse the plan from skill execution output
    4. Clean up cloned repository

    Coordinates repository management and plan generation workflow.
    """

    def __init__(
        self,
        claude_client: ClaudeClient,
        repo_cloner: RepoCloner,
        metadata_extractor: MetadataExtractor | None = None,
    ) -> None:
        """Initialize planning service with Claude client and repo cloner.

        Args:
            claude_client: Generic Claude API client for queries.
            repo_cloner: Repository cloner adapter for git operations.
            metadata_extractor: Metadata extractor for LLM execution data.
                Defaults to new instance if not provided.
        """
        self._client = claude_client
        self._repo_cloner = repo_cloner
        self._metadata_extractor = metadata_extractor or MetadataExtractor()

    async def generate_plan(
        self,
        issue_title: str,
        issue_body: str,
        issue_number: int,
        repo_owner: str,
        repo_name: str,
        target_branch: str | None = None,
    ) -> tuple[Plan, LLMMetadata]:
        """Generate a codebase-aware implementation plan from a GitHub issue.

        This method atomically:
        1. Clones the target repository
        2. Invokes feature-planner skill to create implementation plan
        3. Parses plan from skill output
        4. Cleans up the cloned repository

        Args:
            issue_title: Title of the GitHub issue.
            issue_body: Body/description of the GitHub issue.
            issue_number: Issue number for reference.
            repo_owner: GitHub repository owner.
            repo_name: GitHub repository name.
            target_branch: Branch to analyze (defaults to main/master).

        Returns:
            Tuple of (Plan domain object, LLM execution metadata).

        Raises:
            RuntimeError: If repository cloning or planning fails.
        """
        temp_dir: Path | None = None

        try:
            # Step 1: Clone the repository and capture commit SHA
            temp_dir, repo_path, commit_sha = await self._repo_cloner.clone_to_temp(
                repo_owner, repo_name, target_branch
            )

            # Step 2: Invoke feature-planner skill and parse plan
            plan, llm_metadata = await self._generate_plan_with_skill(
                repo_path, issue_title, issue_body, issue_number, commit_sha
            )

            return plan, llm_metadata

        finally:
            # Step 3: Always cleanup, even if planning fails
            if temp_dir and temp_dir.exists():
                self._repo_cloner.cleanup(temp_dir)

    async def _generate_plan_with_skill(
        self,
        repo_path: Path,
        issue_title: str,
        issue_body: str,
        issue_number: int,
        commit_sha: str,
    ) -> tuple[Plan, LLMMetadata]:
        """Generate implementation plan by invoking feature-planner skill.

        This method uses Claude Agent SDK structured outputs to get a
        validated PlanResponse object that matches our JSON schema.

        Args:
            repo_path: Path to the cloned repository.
            issue_title: Title of the GitHub issue.
            issue_body: Body/description of the GitHub issue.
            issue_number: Issue number for reference.
            commit_sha: Git commit SHA the repository is at.

        Returns:
            Tuple of (Plan domain object, LLM execution metadata).

        Raises:
            RuntimeError: If plan generation fails or returns invalid output.
        """
        # Configure agent options to enable skills with structured outputs
        options = ClaudeAgentOptions(
            cwd=str(repo_path),
            # Enable tools needed by feature-planner skill
            allowed_tools=[
                "Skill",  # Required to invoke skills
                "Task",  # Skills use subagents
                "TodoWrite",  # Skills create task lists
                "Bash",  # Skills need git/gh commands
                "Read",  # For reading code
                "Grep",  # For searching code
                "Glob",  # For finding files
            ],
            # Load global skills (feature-planner) and project skills
            setting_sources=["user", "project"],
            permission_mode="acceptEdits",  # Auto-approve skill operations
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
            },
            # Configure structured outputs with PlanResponse schema
            output_format={
                "type": "json_schema",
                "schema": PlanResponse.model_json_schema(),
            },
        )

        # Invoke feature-planner skill via prompt
        # The skill will be automatically invoked based on description matching
        prompt = f"""Plan implementation for GitHub issue:

Issue #{issue_number}: {issue_title}

{issue_body}

Create a comprehensive implementation plan using Skill(feature-planner).

Return a structured plan with:
- summary: High-level description of what needs to be done
- steps: Ordered list of implementation steps (with id, description, related_files, estimated_complexity)
- technical_approach: Architecture decisions and patterns to use
- testing_strategy: How to test the implementation"""

        # Execute query and collect ALL messages for metadata extraction
        all_messages: list[Any] = []
        plan_response: PlanResponse | None = None
        result_message: Any = None

        async for message in self._client.query(prompt, options):
            all_messages.append(message)

            # Check for structured output
            if hasattr(message, "structured_output") and message.structured_output:
                # Validate and parse the structured output
                plan_response = PlanResponse.model_validate(message.structured_output)

            # Check for result message with metadata
            if hasattr(message, "subtype"):
                result_message = message

        if not plan_response:
            raise RuntimeError("Planning agent did not return structured output")

        # Extract metadata from collected messages
        llm_metadata = self._extract_llm_metadata(all_messages, result_message)

        # Convert PlanResponse to Plan domain model
        plan = self._convert_to_domain_plan(plan_response, issue_number, commit_sha)

        return plan, llm_metadata

    def _convert_to_domain_plan(
        self,
        plan_response: PlanResponse,
        issue_number: int,
        commit_sha: str,
    ) -> Plan:
        """Convert validated PlanResponse to Plan domain model.

        Args:
            plan_response: Validated Pydantic model from structured output.
            issue_number: GitHub issue number for metadata.
            commit_sha: Git commit SHA the plan was based on.

        Returns:
            Plan domain object with steps converted from PlanStepResponse.
        """
        # Convert PlanStepResponse objects to PlanStep domain objects
        # Now includes related_files and estimated_complexity as first-class attributes
        steps = [
            PlanStep(
                id=step.id,
                description=step.description,
                completed=step.completed,
                related_files=step.related_files,
                estimated_complexity=step.estimated_complexity,
            )
            for step in plan_response.steps
        ]

        # Build metadata with issue reference
        # Note: technical_approach and testing_strategy are now first-class Plan attributes
        metadata: dict[str, Any] = {
            "issue_number": issue_number,
        }

        return Plan(
            summary=plan_response.summary,
            steps=steps,
            created_at=datetime.now(),
            technical_approach=plan_response.technical_approach,
            testing_strategy=plan_response.testing_strategy,
            metadata=metadata,
            based_on_commit=commit_sha,
        )

    def _extract_llm_metadata(
        self, messages: list[Any], result_message: Any
    ) -> LLMMetadata:
        """Extract LLM metadata from SDK messages and result.

        Args:
            messages: List of SDK messages from the query execution.
            result_message: The final ResultMessage with cost and usage info.

        Returns:
            LLMMetadata object with extracted information.
        """
        return self._metadata_extractor.extract_metadata(messages, result_message)

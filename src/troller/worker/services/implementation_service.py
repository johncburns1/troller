"""Implementation service for executing codebase changes based on plans.

This service orchestrates the implementation workflow:
1. Clone repository
2. Invoke feature-implementation skill via Claude Agent SDK
3. Commit and push changes
4. Clean up cloned repository
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions

from troller.domain.models.commit import Commit
from troller.domain.models.issue import Issue
from troller.domain.models.plan import Plan
from troller.worker.activities.activity_outputs import LLMMetadataOutput
from troller.worker.activities.llm_metadata import MetadataExtractor
from troller.worker.adapters.claude_client import ClaudeClient
from troller.worker.adapters.git_operations import GitOperations
from troller.worker.adapters.repo_cloner import RepoCloner


class ImplementationService:
    """Service for executing code implementation based on plans.

    This service uses ClaudeClient to:
    1. Clone the target repository
    2. Invoke the feature-implementation skill via Agent SDK
    3. Commit and push changes to the repository
    4. Clean up cloned repository

    Coordinates repository management and implementation workflow.
    """

    def __init__(
        self,
        claude_client: ClaudeClient,
        repo_cloner: RepoCloner,
        git_operations: GitOperations,
        metadata_extractor: MetadataExtractor | None = None,
    ) -> None:
        """Initialize implementation service.

        Args:
            claude_client: Claude API client for queries.
            repo_cloner: Repository cloner adapter for git operations.
            git_operations: Git operations adapter for commits and pushes.
            metadata_extractor: Metadata extractor for LLM execution data.
                Defaults to new instance if not provided.
        """
        self._client = claude_client
        self._repo_cloner = repo_cloner
        self._git_ops = git_operations
        self._metadata_extractor = metadata_extractor or MetadataExtractor()

    async def implement_changes(
        self,
        plan: Plan,
        issue: Issue,
        repo_owner: str,
        repo_name: str,
        branch_name: str,
        target_branch: str | None = None,
    ) -> tuple[list[Commit], LLMMetadataOutput]:
        """Execute code implementation based on plan.

        This method atomically:
        1. Clones the target repository
        2. Invokes feature-implementation skill to write code
        3. Commits and pushes changes
        4. Cleans up the cloned repository

        Args:
            plan: Implementation plan with steps and approach.
            issue: GitHub issue being addressed.
            repo_owner: GitHub repository owner.
            repo_name: GitHub repository name.
            branch_name: Branch name to push changes to.
            target_branch: Base branch to clone from (defaults to main/master).

        Returns:
            Tuple of (list of Commit domain objects, LLM execution metadata).

        Raises:
            RuntimeError: If repository cloning or implementation fails.
        """
        temp_dir: Path | None = None

        try:
            # Step 1: Clone the repository
            temp_dir, repo_path, commit_sha = await self._repo_cloner.clone_to_temp(
                repo_owner, repo_name, target_branch
            )

            # Step 2: Invoke feature-implementation skill and execute implementation
            commits, llm_metadata = await self._implement(
                repo_path, plan, issue, branch_name, commit_sha
            )

            return commits, llm_metadata

        finally:
            # Step 3: Always cleanup, even if implementation fails
            if temp_dir and temp_dir.exists():
                self._repo_cloner.cleanup(temp_dir)

    async def _implement(
        self,
        repo_path: Path,
        plan: Plan,
        issue: Issue,
        branch_name: str,
        base_commit_sha: str,
    ) -> tuple[list[Commit], LLMMetadataOutput]:
        """Execute implementation by invoking feature-implementation skill.

        Args:
            repo_path: Path to the cloned repository.
            plan: Implementation plan with steps and approach.
            issue: GitHub issue being addressed.
            branch_name: Branch name for commits.
            base_commit_sha: Git commit SHA the repository is at.

        Returns:
            Tuple of (list of Commit domain objects, LLM execution metadata).

        Raises:
            RuntimeError: If implementation fails.
        """
        # Configure agent options for feature-implementation skill
        options = ClaudeAgentOptions(
            cwd=str(repo_path),
            # Enable tools needed for feature-implementation skill
            allowed_tools=[
                "Skill",  # Required to invoke skills
                "Task",  # Skills use subagents
                "TodoWrite",  # Skills create task lists
                "Bash",  # Skills need command execution
                "Read",  # For reading code
                "Write",  # For creating files
                "Edit",  # For editing files
                "Grep",  # For searching code
                "Glob",  # For finding files
            ],
            # Load global skills (feature-implementation) and project skills
            setting_sources=["user", "project"],
            permission_mode="bypassPermissions",  # Auto-approve operations
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
            },
        )

        # Build prompt for feature-implementation skill
        prompt = self._build_implementation_prompt(plan, issue, base_commit_sha)

        # Execute query and collect ALL messages for metadata extraction
        all_messages: list[Any] = []
        result_message: Any = None

        async for message in self._client.query(prompt, options):
            all_messages.append(message)

            # Check for result message with metadata
            if hasattr(message, "subtype"):
                result_message = message

        # Extract metadata from collected messages
        llm_metadata = self._extract_llm_metadata(all_messages, result_message)

        # Commit and push changes
        commit = await self._commit_and_push_changes(
            repo_path, issue, plan, branch_name
        )

        return [commit], llm_metadata

    def _build_implementation_prompt(
        self, plan: Plan, issue: Issue, base_commit_sha: str
    ) -> str:
        """Build prompt for Claude to implement the plan.

        Args:
            plan: Implementation plan with steps and approach.
            issue: GitHub issue being addressed.
            base_commit_sha: Git commit SHA the plan was based on.

        Returns:
            Formatted prompt string for Claude.
        """
        # Build steps description
        steps_text = "\n".join(
            [f"{i + 1}. {step.description}" for i, step in enumerate(plan.steps)]
        )

        # Build technical context
        technical_context = ""
        if plan.technical_approach:
            technical_context += f"\n\nTechnical Approach:\n{plan.technical_approach}"
        if plan.testing_strategy:
            technical_context += f"\n\nTesting Strategy:\n{plan.testing_strategy}"

        return f"""Implement changes for GitHub issue #{issue.number}: {issue.title}

Issue Description:
{issue.description}

Implementation Plan:
{plan.summary}

Steps:
{steps_text}
{technical_context}

Base Commit: {base_commit_sha}

Use Skill(feature-implementation) to implement these changes following the plan.
Write clean, tested code following the project's engineering standards.
The implementation should address the issue requirements and follow the technical approach specified."""

    async def _commit_and_push_changes(
        self, repo_path: Path, issue: Issue, plan: Plan, branch_name: str
    ) -> Commit:
        """Commit implemented changes and push to remote.

        Args:
            repo_path: Path to the repository with changes.
            issue: GitHub issue for commit message.
            plan: Implementation plan for commit message.
            branch_name: Branch to push to.

        Returns:
            Commit domain object with SHA and metadata.
        """
        # Build commit message
        commit_message = f"""Implement {plan.summary}

Addresses issue #{issue.number}: {issue.title}

This implementation follows the planned approach and includes:
- Code changes based on implementation plan
- Tests following TDD principles
- Quality checks (ruff, mypy, pytest)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"""

        # Commit all changes
        await self._git_ops.commit_changes(
            repo_path=str(repo_path), message=commit_message, files=None
        )

        # Get commit SHA
        commit_sha = await self._git_ops.get_current_sha(str(repo_path))

        # Push to remote
        await self._git_ops.push_branch(
            repo_path=str(repo_path),
            branch_name=branch_name,
            force=False,
            set_upstream=True,
        )

        # Return Commit domain model
        return Commit(
            sha=commit_sha,
            message=commit_message,
            timestamp=datetime.now(UTC),
            internal_review_feedback=None,
        )

    def _extract_llm_metadata(
        self, messages: list[Any], result_message: Any
    ) -> LLMMetadataOutput:
        """Extract LLM metadata from SDK messages and result.

        Args:
            messages: List of SDK messages from the query execution.
            result_message: The final ResultMessage with cost and usage info.

        Returns:
            LLMMetadataOutput object with extracted information.
        """
        return self._metadata_extractor.extract_metadata(messages, result_message)

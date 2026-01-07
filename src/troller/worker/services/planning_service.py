"""Planning service for generating codebase-aware implementation plans.

This service orchestrates the plan generation workflow:
1. Clone repository
2. Invoke feature-planner skill via Claude Agent SDK
3. Parse plan from skill output
4. Clean up cloned repository
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions

from troller.domain.models.plan import Plan, PlanStep
from troller.worker.adapters.claude_client import ClaudeClient
from troller.worker.adapters.repo_cloner import RepoCloner


class PlanningService:
    """Service for generating codebase-aware implementation plans.

    This service uses ClaudeClient to:
    1. Clone the target repository
    2. Invoke the feature-planner skill via Agent SDK
    3. Parse the plan from skill execution output
    4. Clean up cloned repository

    Coordinates repository management and plan generation workflow.
    """

    def __init__(self, claude_client: ClaudeClient, repo_cloner: RepoCloner) -> None:
        """Initialize planning service with Claude client and repo cloner.

        Args:
            claude_client: Generic Claude API client for queries.
            repo_cloner: Repository cloner adapter for git operations.
        """
        self._client = claude_client
        self._repo_cloner = repo_cloner

    async def generate_plan(
        self,
        issue_title: str,
        issue_body: str,
        issue_number: int,
        repo_owner: str,
        repo_name: str,
        target_branch: str | None = None,
    ) -> Plan:
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
            Plan domain object with implementation steps from skill execution.

        Raises:
            RuntimeError: If repository cloning or planning fails.
        """
        temp_dir: Path | None = None

        try:
            # Step 1: Clone the repository
            temp_dir, repo_path = await self._repo_cloner.clone_to_temp(
                repo_owner, repo_name, target_branch
            )

            # Step 2: Invoke feature-planner skill and parse plan
            plan = await self._generate_plan_with_skill(
                repo_path, issue_title, issue_body, issue_number
            )

            return plan

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
    ) -> Plan:
        """Generate implementation plan by invoking feature-planner skill.

        Args:
            repo_path: Path to the cloned repository.
            issue_title: Title of the GitHub issue.
            issue_body: Body/description of the GitHub issue.
            issue_number: Issue number for reference.

        Returns:
            Plan domain object with implementation steps.

        Raises:
            RuntimeError: If plan generation fails.
        """
        # Configure agent options to enable skills
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
        )

        # Invoke feature-planner skill via prompt
        # The skill will be automatically invoked based on description matching
        prompt = f"""Plan implementation for GitHub issue:

Issue #{issue_number}: {issue_title}

{issue_body}

Create a comprehensive implementation plan using Skill(feature-planner)"""

        # Collect all messages from skill execution
        messages = []
        async for message in self._client.query(prompt, options):
            messages.append(message)

        # Parse plan from skill output
        return self._parse_plan_from_messages(messages, issue_number)

    def _parse_plan_from_messages(self, messages: list[Any], issue_number: int) -> Plan:
        """Parse Plan domain object from skill execution messages.

        Extracts plan summary, steps, and metadata from the free-form
        output of the feature-planner skill.

        Args:
            messages: List of messages from skill execution.
            issue_number: GitHub issue number for metadata.

        Returns:
            Plan domain object constructed from messages.
        """
        plan_text = self._extract_plan_text(messages)
        steps = self._extract_steps_from_messages(messages)
        summary = self._extract_summary(plan_text)

        return Plan(
            summary=summary,
            steps=steps,
            created_at=datetime.now(),
            metadata={
                "issue_number": issue_number,
                "skill_output": plan_text[:1000],  # Store first 1000 chars
            },
        )

    def _extract_plan_text(self, messages: list[Any]) -> str:
        """Extract all text content from assistant messages.

        Args:
            messages: List of messages from skill execution.

        Returns:
            Combined plan text from all assistant messages.
        """
        plan_text_parts = []

        for message in messages:
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "text"):
                        plan_text_parts.append(block.text)

        return "\n\n".join(plan_text_parts)

    def _extract_steps_from_messages(self, messages: list[Any]) -> list[PlanStep]:
        """Extract implementation steps from TodoWrite tool uses.

        Args:
            messages: List of messages from skill execution.

        Returns:
            List of PlanStep objects extracted from TodoWrite calls.
        """
        steps = []

        for message in messages:
            if hasattr(message, "content"):
                for block in message.content:
                    if hasattr(block, "name") and block.name == "TodoWrite":
                        if hasattr(block, "input") and "todos" in block.input:
                            for i, todo in enumerate(block.input["todos"]):
                                step = PlanStep(
                                    id=f"step-{i + 1}",
                                    description=todo.get("content", ""),
                                    completed=False,
                                )
                                steps.append(step)

        return steps

    def _extract_summary(self, plan_text: str) -> str:
        """Extract plan summary from full plan text.

        Finds the first non-empty, non-heading line as the summary.

        Args:
            plan_text: Full plan text from skill output.

        Returns:
            Extracted summary or default text.
        """
        summary_lines = [
            line.strip()
            for line in plan_text.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]

        return summary_lines[0] if summary_lines else "Implementation plan"

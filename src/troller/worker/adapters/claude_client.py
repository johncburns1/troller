"""Claude API client adapter.

Adapter for interacting with Claude AI via Agent SDK for codebase-aware planning.
"""

import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Literal

from anthropic import Anthropic
from claude_agent_sdk import ClaudeAgentOptions, query  # type: ignore[import-not-found]
from pydantic import BaseModel, Field

from troller.domain.models.plan import Plan, PlanStep


class PlanStepResponse(BaseModel):
    """Pydantic model for LLM-generated plan step (structured output)."""

    id: str = Field(..., description="Unique identifier for the step (e.g., 'step-1')")
    description: str = Field(..., description="Detailed description of the step")
    completed: bool = Field(default=False, description="Whether this step is completed")
    related_files: list[str] | None = Field(
        default=None, description="Files that will be modified in this step"
    )
    estimated_complexity: Literal["simple", "moderate", "complex"] | None = Field(
        default=None, description="Estimated complexity of the step"
    )


class PlanResponse(BaseModel):
    """Pydantic model for LLM-generated plan (structured output)."""

    summary: str = Field(..., description="High-level summary of what needs to be done")
    steps: list[PlanStepResponse] = Field(
        ..., description="Ordered list of implementation steps"
    )
    technical_approach: str | None = Field(
        default=None, description="Architecture decisions, libraries, patterns to use"
    )
    testing_strategy: str | None = Field(
        default=None, description="How to test the implementation"
    )


class ClaudeClient:
    """Claude Agent SDK client for generating codebase-aware implementation plans.

    This adapter uses the Claude Agent SDK to:
    1. Clone the target repository
    2. Explore the codebase with AI agent tools (Read, Glob, Grep)
    3. Generate an informed implementation plan
    4. Clean up cloned repository

    Authenticates using Anthropic API key from environment.
    """

    def __init__(self) -> None:
        """Initialize Claude client with API key authentication.

        Raises:
            ValueError: If ANTHROPIC_API_KEY environment variable is not set.
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        # Store API key for agent options and direct API calls
        self._api_key = api_key
        self._anthropic_client = Anthropic(api_key=api_key)

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
        2. Explores the codebase using AI agent tools
        3. Generates an implementation plan with full context
        4. Cleans up the cloned repository

        Args:
            issue_title: Title of the GitHub issue.
            issue_body: Body/description of the GitHub issue.
            issue_number: Issue number for reference.
            repo_owner: GitHub repository owner.
            repo_name: GitHub repository name.
            target_branch: Branch to analyze (defaults to main/master).

        Returns:
            Plan domain object with implementation steps informed by codebase analysis.

        Raises:
            RuntimeError: If repository cloning or planning fails.
        """
        temp_dir: Path | None = None

        try:
            # Step 1: Clone the repository
            temp_dir, repo_path = await self._clone_repository(
                repo_owner, repo_name, target_branch
            )

            # Step 2: Explore codebase and generate plan
            plan = await self._generate_plan_with_context(
                repo_path, issue_title, issue_body, issue_number
            )

            return plan

        finally:
            # Step 3: Always cleanup, even if planning fails
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    async def _clone_repository(
        self, repo_owner: str, repo_name: str, target_branch: str | None
    ) -> tuple[Path, Path]:
        """Clone a GitHub repository to a temporary directory.

        Args:
            repo_owner: GitHub repository owner.
            repo_name: GitHub repository name.
            target_branch: Branch to clone (tries main then master if None).

        Returns:
            Tuple of (temp_dir_path, cloned_repo_path).

        Raises:
            RuntimeError: If git clone fails.
        """
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp(prefix=f"troller_{repo_name}_"))
        clone_path = temp_dir / repo_name

        # Construct repository URL
        repo_url = f"https://github.com/{repo_owner}/{repo_name}.git"

        # Determine branch to clone
        branch = target_branch or "main"

        # Clone the repository (shallow clone for speed)
        try:
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    branch,
                    repo_url,
                    str(clone_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            return temp_dir, clone_path

        except subprocess.CalledProcessError:
            # If main branch doesn't exist and no specific branch was requested, try master
            if branch == "main" and target_branch is None:
                try:
                    subprocess.run(
                        [
                            "git",
                            "clone",
                            "--depth",
                            "1",
                            "--branch",
                            "master",
                            repo_url,
                            str(clone_path),
                        ],
                        capture_output=True,
                        text=True,
                        check=True,
                    )

                    return temp_dir, clone_path

                except subprocess.CalledProcessError as e:
                    # Clean up and raise
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    raise RuntimeError(
                        f"Failed to clone {repo_url} on both main and master branches: {e.stderr}"
                    ) from e

            # Clean up and raise
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to clone {repo_url} on branch {branch}")

    async def _generate_plan_with_context(
        self,
        repo_path: Path,
        issue_title: str,
        issue_body: str,
        issue_number: int,
    ) -> Plan:
        """Generate implementation plan using codebase context via Agent SDK.

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
        # Configure agent options
        options = ClaudeAgentOptions(
            cwd=str(repo_path),
            allowed_tools=["Read", "Bash", "Glob", "Grep"],
            permission_mode="bypassPermissions",  # Auto-approve read-only operations
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": """You are an expert software architect analyzing GitHub issues.

Your task is to:
1. Explore the codebase structure and architecture
2. Understand existing patterns and conventions
3. Analyze the issue requirements
4. Create a detailed, actionable implementation plan

Be thorough in your codebase exploration to ensure the plan aligns with existing architecture.""",
            },
        )

        # Phase 1: Explore the codebase
        exploration_prompt = """Analyze this codebase to understand its structure:

1. Find and read key documentation files (README.md, ARCHITECTURE.md, CLAUDE.md, etc.)
2. Identify the main directory structure and tech stack
3. Understand the architecture pattern (hexagonal, layered, MVC, etc.)
4. Find key entry points and core modules
5. Identify coding conventions and patterns

Provide a concise summary of the codebase architecture and key findings."""

        codebase_analysis = []
        async for message in query(prompt=exploration_prompt, options=options):
            if hasattr(message, "result") and message.result:
                codebase_analysis.append(message.result)

        architecture_summary = "\n".join(codebase_analysis)

        # Phase 2: Generate the implementation plan with structured output
        planning_prompt = f"""Based on the codebase analysis, create a detailed implementation plan for this GitHub issue.

GITHUB ISSUE:
Title: {issue_title}
Description:
{issue_body}

CODEBASE ANALYSIS:
{architecture_summary}

Create a comprehensive implementation plan with:
- A high-level summary of what needs to be done
- Specific, actionable steps in logical order
- File paths for files that will be modified (from the actual codebase)
- Complexity estimates for each step (simple/moderate/complex)
- Technical approach explaining architecture decisions and patterns
- Testing strategy for validating the implementation

Requirements:
- Steps should follow the existing architecture patterns identified in the analysis
- Keep plans focused on the issue requirements
- Order steps with dependencies in mind"""

        # Use structured output to guarantee valid schema
        # Note: response_format is passed via extra_body for type compatibility
        response = self._anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            messages=[{"role": "user", "content": planning_prompt}],
            extra_body={
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "implementation_plan",
                        "schema": PlanResponse.model_json_schema(),
                        "strict": True,
                    },
                }
            },
        )

        # Parse structured output - guaranteed to match schema
        # Extract text from first content block (guaranteed to be TextBlock for our request)
        first_content = response.content[0]
        response_text = first_content.text if hasattr(first_content, "text") else ""
        plan_data = PlanResponse.model_validate_json(response_text)

        # Convert Pydantic response model to domain model
        steps = [
            PlanStep(
                id=step.id,
                description=step.description,
                completed=step.completed,
                related_files=step.related_files,
                estimated_complexity=step.estimated_complexity,
            )
            for step in plan_data.steps
        ]

        return Plan(
            summary=plan_data.summary,
            steps=steps,
            created_at=datetime.now(),
            metadata={
                "issue_number": issue_number,
                "codebase_analysis": architecture_summary,
            },
            technical_approach=plan_data.technical_approach,
            testing_strategy=plan_data.testing_strategy,
        )

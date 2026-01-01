"""Claude API client adapter.

Adapter for interacting with Claude AI via Anthropic SDK.
"""

import os
from datetime import datetime
from typing import Any

from anthropic import Anthropic
from anthropic.types import MessageParam, ToolParam

from troller.domain.models.plan import Plan, PlanStep


class ClaudeClient:
    """Claude API client for generating implementation plans.

    This is an adapter that wraps the Anthropic SDK to provide AI planning
    capabilities. Authenticates using Anthropic API key from environment.
    """

    def __init__(self) -> None:
        """Initialize Claude client with API key authentication.

        Raises:
            ValueError: If ANTHROPIC_API_KEY environment variable is not set.
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")

        self._client = Anthropic(api_key=api_key)

    def generate_plan(
        self, issue_title: str, issue_body: str, issue_number: int
    ) -> Plan:
        """Generate an implementation plan from a GitHub issue.

        Args:
            issue_title: Title of the GitHub issue.
            issue_body: Body/description of the GitHub issue.
            issue_number: Issue number for reference.

        Returns:
            Plan domain object with implementation steps.
        """
        system_prompt = """You are a senior software architect analyzing GitHub issues to create implementation plans.

Your task is to analyze the issue and create a structured implementation plan with:
- A high-level summary of what needs to be done
- Ordered implementation steps
- Technical approach and architecture decisions
- Testing strategy

Keep plans simple and focused on the issue requirements."""

        user_message = f"""Analyze this GitHub issue and create an implementation plan:

Issue #{issue_number}: {issue_title}

{issue_body}

Create a structured plan with implementation steps."""

        # Define the tool schema for structured output
        tools: list[ToolParam] = [
            {
                "name": "create_plan",
                "description": "Create a structured implementation plan",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "High-level summary of the plan",
                        },
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "description": {"type": "string"},
                                    "completed": {"type": "boolean"},
                                    "related_files": {
                                        "type": ["array", "null"],
                                        "items": {"type": "string"},
                                    },
                                    "estimated_complexity": {
                                        "type": ["string", "null"],
                                        "enum": ["simple", "moderate", "complex", None],
                                    },
                                },
                                "required": ["id", "description", "completed"],
                            },
                        },
                        "technical_approach": {
                            "type": ["string", "null"],
                            "description": "Architecture decisions and technical approach",
                        },
                        "testing_strategy": {
                            "type": ["string", "null"],
                            "description": "How to test the implementation",
                        },
                    },
                    "required": ["summary", "steps"],
                },
            }
        ]

        messages: list[MessageParam] = [{"role": "user", "content": user_message}]

        response = self._client.messages.create(
            model="claude-opus-4-5-20251101",
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            tools=tools,
            tool_choice={"type": "tool", "name": "create_plan"},
        )

        # Extract the structured output from tool use
        tool_use = next(block for block in response.content if block.type == "tool_use")
        plan_data: dict[str, Any] = tool_use.input

        # Convert to domain model
        steps = [
            PlanStep(
                id=str(step["id"]),
                description=str(step["description"]),
                completed=bool(step["completed"]),
                related_files=step.get("related_files"),
                estimated_complexity=step.get("estimated_complexity"),
            )
            for step in plan_data["steps"]
        ]

        return Plan(
            summary=str(plan_data["summary"]),
            steps=steps,
            created_at=datetime.now(),
            metadata={"issue_number": issue_number},
            technical_approach=plan_data.get("technical_approach"),
            testing_strategy=plan_data.get("testing_strategy"),
        )

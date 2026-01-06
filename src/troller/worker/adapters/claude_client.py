"""Claude API client adapter.

Generic adapter for interacting with Claude AI via Agent SDK and Messages API.
Provides reusable methods for AI queries with codebase awareness and structured outputs.
"""

import os
from collections.abc import AsyncIterator
from typing import Any

from anthropic import Anthropic
from claude_agent_sdk import ClaudeAgentOptions, query as agent_query
from pydantic import BaseModel


class ClaudeClient:
    """Generic Claude API client for AI queries.

    This adapter provides a thin wrapper around Claude APIs:
    - Agent SDK for codebase-aware queries with tool access
    - Messages API for structured output queries

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

    async def query(
        self, prompt: str, options: ClaudeAgentOptions
    ) -> AsyncIterator[Any]:
        """Execute generic agent SDK query with codebase tools.

        Uses Claude Agent SDK to execute queries with access to codebase tools
        (Read, Glob, Grep, Bash) based on the provided options.

        Args:
            prompt: The query prompt to send to Claude.
            options: Agent SDK options including cwd, allowed_tools, permission_mode.

        Yields:
            Agent SDK message responses from the query execution.

        Example:
            ```python
            options = ClaudeAgentOptions(
                cwd="/path/to/repo",
                allowed_tools=["Read", "Glob", "Grep"],
                permission_mode="bypassPermissions",
            )
            async for message in client.query("Analyze the codebase", options):
                if hasattr(message, "result"):
                    print(message.result)
            ```
        """
        async for message in agent_query(prompt=prompt, options=options):
            yield message

    async def structured_query(
        self,
        prompt: str,
        schema: type[BaseModel],
        model: str = "claude-sonnet-4-5-20250929",
        token_limit: int = 4096,
    ) -> BaseModel:
        """Query Claude with structured output guarantee.

        Uses Claude Messages API with JSON schema validation to ensure the response
        matches the provided Pydantic schema exactly.

        Args:
            prompt: The query prompt to send to Claude.
            schema: Pydantic model class defining the expected response structure.
            model: Claude model to use (defaults to Sonnet 4.5).
            token_limit: Maximum tokens for the response (defaults to 4096).

        Returns:
            Validated Pydantic model instance matching the schema.

        Example:
            ```python
            class AnalysisResult(BaseModel):
                summary: str
                findings: list[str]

            result = await client.structured_query(
                "Analyze the architecture",
                AnalysisResult
            )
            print(result.summary)
            ```
        """
        # Use structured output to guarantee valid schema
        # Note: response_format is passed via extra_body for type compatibility
        response = self._anthropic_client.messages.create(
            model=model,
            max_tokens=token_limit,
            messages=[{"role": "user", "content": prompt}],
            extra_body={
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "query_response",
                        "schema": schema.model_json_schema(),
                        "strict": True,
                    },
                }
            },
        )

        # Parse structured output - guaranteed to match schema
        # Extract text from first content block (guaranteed to be TextBlock for our request)
        first_content = response.content[0]
        response_text = first_content.text if hasattr(first_content, "text") else ""
        return schema.model_validate_json(response_text)

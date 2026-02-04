"""Claude API client adapter.

Generic adapter for interacting with Claude AI via Agent SDK and Messages API.
Provides reusable methods for AI queries with codebase awareness and structured outputs.
"""

import os
from collections.abc import AsyncIterator
from typing import Any

from anthropic import Anthropic, AnthropicBedrock
from claude_agent_sdk import ClaudeAgentOptions, query as agent_query
from pydantic import BaseModel

from troller.config import config


class ClaudeClient:
    """Generic Claude API client for AI queries.

    This adapter provides a thin wrapper around Claude APIs:
    - Agent SDK for codebase-aware queries with tool access
    - Messages API for structured output queries

    Supports both Anthropic API and AWS Bedrock as providers.
    Provider selection is controlled via config.llm_provider.provider.
    """

    def __init__(self, model: str | None = None) -> None:
        """Initialize Claude client with provider-specific authentication.

        Args:
            model: Optional default model to use for queries. If not specified,
                queries will use the default model from structured_query.

        Raises:
            ValueError: If using Anthropic provider and ANTHROPIC_API_KEY is not set.
        """
        self._provider = config.llm_provider.provider
        self._model = model

        if self._provider == "bedrock":
            # Configure Agent SDK for Bedrock
            os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"
            if config.llm_provider.bedrock_region:
                os.environ["AWS_REGION"] = config.llm_provider.bedrock_region

            # Create Bedrock client for structured queries
            self._anthropic_client: Anthropic | AnthropicBedrock = AnthropicBedrock(
                aws_region=config.llm_provider.bedrock_region,
            )
            self._api_key: str | None = None  # Not needed for Bedrock
        else:
            # Anthropic provider
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is required")
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

    def _get_effective_model(self, model: str | None) -> str:
        """Get effective model ID, converting to Bedrock format if needed.

        Args:
            model: Optional model ID to use. Falls back to instance model or default.

        Returns:
            Model ID appropriate for the configured provider.
        """
        effective_model = model or self._model or "claude-sonnet-4-5-20250929"

        if self._provider == "bedrock":
            return self._to_bedrock_model_id(effective_model)
        return effective_model

    def _to_bedrock_model_id(self, model: str) -> str:
        """Convert Anthropic model ID to Bedrock global model ID.

        Args:
            model: Anthropic-style model ID (e.g., 'claude-opus-4-5-20251101').

        Returns:
            Bedrock global model ID (e.g., 'global.anthropic.claude-opus-4-5-20251101-v1:0').
        """
        # Handle if already in Bedrock format
        if model.startswith("anthropic.") or model.startswith("global."):
            return model

        # Convert: claude-opus-4-5-20251101 -> global.anthropic.claude-opus-4-5-20251101-v1:0
        return f"global.anthropic.{model}-v1:0"

    async def structured_query(
        self,
        prompt: str,
        schema: type[BaseModel],
        model: str | None = None,
        token_limit: int = 4096,
    ) -> BaseModel:
        """Query Claude with structured output guarantee.

        Uses Claude Messages API with JSON schema validation to ensure the response
        matches the provided Pydantic schema exactly.

        Args:
            prompt: The query prompt to send to Claude.
            schema: Pydantic model class defining the expected response structure.
            model: Claude model to use. If not specified, uses instance model
                (from __init__) or defaults to Sonnet 4.5.
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
        # Get effective model with provider-specific formatting
        effective_model = self._get_effective_model(model)

        # Use structured output to guarantee valid schema
        # Note: response_format is passed via extra_body for type compatibility
        response = self._anthropic_client.messages.create(
            model=effective_model,
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

"""Claude API client adapter.

Generic adapter for interacting with Claude AI via Agent SDK and Messages API.
Provides reusable methods for AI queries with codebase awareness and structured outputs.
"""

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic, AnthropicBedrock
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query as agent_query
from pydantic import BaseModel

from troller.config import config


@dataclass(frozen=True)
class StructuredQueryResult[T]:
    """Result from structured_query including usage information.

    Attributes:
        result: The validated Pydantic model result.
        input_tokens: Number of input tokens used.
        output_tokens: Number of output tokens generated.
        model: The model that was used.
    """

    result: T
    input_tokens: int
    output_tokens: int
    model: str


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

    async def structured_query[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        model: str | None = None,
        token_limit: int = 4096,
        max_turns: int = 5,
    ) -> StructuredQueryResult[T]:
        """Query Claude with structured output guarantee.

        Uses Claude Agent SDK with output_format option to ensure the response
        matches the provided Pydantic schema exactly.

        Args:
            prompt: The query prompt to send to Claude.
            schema: Pydantic model class defining the expected response structure.
            model: Claude model to use. If not specified, uses instance model
                (from __init__) or defaults to Sonnet 4.5.
            token_limit: Maximum tokens for the response (defaults to 4096).
            max_turns: Maximum conversation turns for the query (defaults to 5).
                Use higher values when the query may require tool usage.

        Returns:
            StructuredQueryResult containing the validated result and usage info.

        Example:
            ```python
            class AnalysisResult(BaseModel):
                summary: str
                findings: list[str]

            query_result = await client.structured_query(
                "Analyze the architecture",
                AnalysisResult
            )
            print(query_result.result.summary)
            print(f"Tokens used: {query_result.input_tokens}")
            ```
        """
        # Get effective model - for Agent SDK, we use simple names like "sonnet"
        effective_model = self._get_agent_sdk_model(model)

        # Use Agent SDK with output_format for structured output
        options = ClaudeAgentOptions(
            model=effective_model,
            max_turns=max_turns,
            permission_mode="bypassPermissions",
            output_format={
                "type": "json_schema",
                "schema": schema.model_json_schema(),
            },
        )

        result_message: ResultMessage | None = None
        async for message in agent_query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                result_message = message
                break

        if result_message is None:
            raise RuntimeError("No result message received from Agent SDK")

        if result_message.structured_output is None:
            raise RuntimeError(
                f"No structured output in result (subtype: {result_message.subtype})"
            )

        # Validate the structured output against the schema
        result = schema.model_validate(result_message.structured_output)

        # Extract token usage from result message
        usage = result_message.usage or {}
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        # Get the actual model used (from usage or fall back to requested)
        actual_model = effective_model

        return StructuredQueryResult(
            result=result,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=actual_model,
        )

    def _get_agent_sdk_model(self, model: str | None) -> str:
        """Get model name for Agent SDK.

        Agent SDK uses simple model names like 'sonnet', 'opus', 'haiku'.

        Args:
            model: Optional model ID to use. Falls back to instance model or default.

        Returns:
            Model name appropriate for Agent SDK.
        """
        effective_model = model or self._model or "claude-sonnet-4-5-20250929"

        # Map full model names to Agent SDK names
        model_mapping = {
            "claude-sonnet-4-5-20250929": "sonnet",
            "claude-opus-4-5-20251101": "opus",
            "claude-haiku-3-5-20241022": "haiku",
        }

        # Check if it's already a simple name
        if effective_model in ("sonnet", "opus", "haiku"):
            return effective_model

        # Try to map from full name
        return model_mapping.get(effective_model, "sonnet")

"""Domain model for LLM execution metadata.

Pure business logic with no external dependencies.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LLMMetadata:
    """Metadata from LLM execution for observability and cost tracking.

    Attributes:
        total_cost_usd: Total cost of the LLM execution in USD.
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.
        duration_ms: Total execution duration in milliseconds.
        duration_api_ms: Time spent in API calls in milliseconds.
        num_turns: Number of conversation turns.
        model: Claude model used for execution.
        tools_used: List of all tools used during execution (Read, Grep, Skill, etc.).
        execution_flow: Auto-generated brief summary of execution approach.
    """

    total_cost_usd: float | None
    input_tokens: int | None
    output_tokens: int | None
    duration_ms: int
    duration_api_ms: int
    num_turns: int
    model: str | None
    tools_used: list[str] = field(default_factory=list)
    execution_flow: str = ""

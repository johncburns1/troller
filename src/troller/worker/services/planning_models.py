"""Pydantic models for plan generation responses.

These models define the structure for LLM-generated implementation plans.
Used for structured output validation when generating plans via Claude API.
"""

from typing import Literal

from pydantic import BaseModel, Field


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

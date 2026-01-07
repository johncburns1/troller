"""Temporal data converter for Pydantic model serialization.

Enables Temporal to serialize/deserialize Pydantic v2 models in workflow and
activity inputs/outputs using Temporal's official contrib integration.
"""

# Use Temporal's official Pydantic v2 data converter
# This properly handles Pydantic v2's model_dump/model_validate methods
from temporalio.contrib.pydantic import pydantic_data_converter

__all__ = ["pydantic_data_converter"]

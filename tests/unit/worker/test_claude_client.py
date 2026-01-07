"""Unit tests for Claude API client adapter."""

import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from troller.worker.adapters.claude_client import ClaudeClient


class TestClaudeClient:
    """Test suite for generic ClaudeClient adapter."""

    def test_init_stores_api_key_from_env(self) -> None:
        """ClaudeClient reads and stores ANTHROPIC_API_KEY from environment."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            client = ClaudeClient()
            assert client._api_key == "test-key"
            assert client._anthropic_client is not None

    def test_init_raises_error_when_api_key_missing(self) -> None:
        """ClaudeClient raises clear error when ANTHROPIC_API_KEY is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="ANTHROPIC_API_KEY environment variable is required"
            ):
                ClaudeClient()

    def test_init_accepts_optional_model_parameter(self) -> None:
        """ClaudeClient.__init__() accepts optional model parameter."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            client = ClaudeClient(model="claude-opus-4-5-20251101")
            assert client._model == "claude-opus-4-5-20251101"

    def test_init_stores_model_when_provided(self) -> None:
        """ClaudeClient.__init__() stores model correctly when provided."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            client = ClaudeClient(model="custom-model")
            assert hasattr(client, "_model")
            assert client._model == "custom-model"

    def test_init_defaults_model_to_none_when_not_provided(self) -> None:
        """ClaudeClient.__init__() defaults model to None when not provided."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            client = ClaudeClient()
            assert client._model is None

    @pytest.mark.asyncio
    async def test_query_yields_agent_sdk_messages(self) -> None:
        """query() yields messages from Agent SDK query."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.agent_query"
            ) as mock_query:
                # Mock Agent SDK query response
                async def mock_query_response(*args, **kwargs):
                    yield MagicMock(result="First message")
                    yield MagicMock(result="Second message")

                mock_query.side_effect = mock_query_response

                client = ClaudeClient()
                options = MagicMock()  # ClaudeAgentOptions mock

                # Collect yielded messages
                messages = []
                async for message in client.query("Test prompt", options):
                    messages.append(message)

                # Verify messages were yielded
                assert len(messages) == 2
                assert messages[0].result == "First message"
                assert messages[1].result == "Second message"

                # Verify agent_query was called with correct parameters
                mock_query.assert_called_once_with(
                    prompt="Test prompt", options=options
                )

    @pytest.mark.asyncio
    async def test_query_passes_options_to_agent_sdk(self) -> None:
        """query() passes ClaudeAgentOptions to agent SDK."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.agent_query"
            ) as mock_query:
                # Mock Agent SDK query response
                async def mock_query_response(*args, **kwargs):
                    yield MagicMock(result="Response")

                mock_query.side_effect = mock_query_response

                client = ClaudeClient()
                options = MagicMock(
                    cwd="/test/path",
                    allowed_tools=["Read", "Grep"],
                    permission_mode="bypassPermissions",
                )

                # Execute query
                async for _ in client.query("Analyze code", options):
                    pass

                # Verify options were passed
                call_kwargs = mock_query.call_args.kwargs
                assert call_kwargs["options"] == options

    @pytest.mark.asyncio
    async def test_structured_query_returns_validated_model(self) -> None:
        """structured_query() returns Pydantic model validated from response."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.Anthropic"
            ) as mock_anthropic_class:
                # Define test schema
                class TestSchema(BaseModel):
                    summary: str
                    count: int

                # Mock Anthropic client response
                mock_anthropic = MagicMock()
                mock_anthropic_class.return_value = mock_anthropic
                mock_response = MagicMock()
                mock_response.content = [
                    MagicMock(text='{"summary": "Test summary", "count": 42}')
                ]
                mock_anthropic.messages.create.return_value = mock_response

                client = ClaudeClient()
                result = await client.structured_query("Generate test data", TestSchema)

                # Verify result is validated Pydantic model
                assert isinstance(result, TestSchema)
                assert result.summary == "Test summary"
                assert result.count == 42

    @pytest.mark.asyncio
    async def test_structured_query_uses_json_schema(self) -> None:
        """structured_query() configures API with JSON schema validation."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.Anthropic"
            ) as mock_anthropic_class:
                # Define test schema
                class TestSchema(BaseModel):
                    name: str

                # Mock Anthropic client response
                mock_anthropic = MagicMock()
                mock_anthropic_class.return_value = mock_anthropic
                mock_response = MagicMock()
                mock_response.content = [MagicMock(text='{"name": "test"}')]
                mock_anthropic.messages.create.return_value = mock_response

                client = ClaudeClient()
                await client.structured_query("Query", TestSchema, model="test-model")

                # Verify messages.create was called with schema
                create_call = mock_anthropic.messages.create.call_args
                assert create_call.kwargs["model"] == "test-model"
                assert create_call.kwargs["max_tokens"] == 4096
                assert "response_format" in create_call.kwargs["extra_body"]

                # Verify schema configuration
                response_format = create_call.kwargs["extra_body"]["response_format"]
                assert response_format["type"] == "json_schema"
                assert response_format["json_schema"]["strict"] is True
                assert "schema" in response_format["json_schema"]

    @pytest.mark.asyncio
    async def test_structured_query_defaults_to_sonnet_model(self) -> None:
        """structured_query() uses Sonnet 4.5 by default."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.Anthropic"
            ) as mock_anthropic_class:
                # Define test schema
                class TestSchema(BaseModel):
                    value: str

                # Mock Anthropic client response
                mock_anthropic = MagicMock()
                mock_anthropic_class.return_value = mock_anthropic
                mock_response = MagicMock()
                mock_response.content = [MagicMock(text='{"value": "test"}')]
                mock_anthropic.messages.create.return_value = mock_response

                client = ClaudeClient()
                await client.structured_query("Query", TestSchema)  # No model specified

                # Verify default model
                create_call = mock_anthropic.messages.create.call_args
                assert create_call.kwargs["model"] == "claude-sonnet-4-5-20250929"

    @pytest.mark.asyncio
    async def test_structured_query_uses_instance_model_when_no_parameter(self) -> None:
        """structured_query() uses instance model when no model parameter provided."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.Anthropic"
            ) as mock_anthropic_class:
                # Define test schema
                class TestSchema(BaseModel):
                    result: str

                # Mock Anthropic client response
                mock_anthropic = MagicMock()
                mock_anthropic_class.return_value = mock_anthropic
                mock_response = MagicMock()
                mock_response.content = [MagicMock(text='{"result": "success"}')]
                mock_anthropic.messages.create.return_value = mock_response

                client = ClaudeClient(model="claude-opus-4-5-20251101")
                await client.structured_query("Query", TestSchema)

                # Verify instance model was used
                create_call = mock_anthropic.messages.create.call_args
                assert create_call.kwargs["model"] == "claude-opus-4-5-20251101"

    @pytest.mark.asyncio
    async def test_structured_query_parameter_overrides_instance_model(self) -> None:
        """structured_query() parameter overrides instance model."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.Anthropic"
            ) as mock_anthropic_class:
                # Define test schema
                class TestSchema(BaseModel):
                    data: str

                # Mock Anthropic client response
                mock_anthropic = MagicMock()
                mock_anthropic_class.return_value = mock_anthropic
                mock_response = MagicMock()
                mock_response.content = [MagicMock(text='{"data": "test"}')]
                mock_anthropic.messages.create.return_value = mock_response

                client = ClaudeClient(model="claude-opus-4-5-20251101")
                await client.structured_query(
                    "Query", TestSchema, model="claude-haiku-override"
                )

                # Verify parameter overrode instance model
                create_call = mock_anthropic.messages.create.call_args
                assert create_call.kwargs["model"] == "claude-haiku-override"

    @pytest.mark.asyncio
    async def test_structured_query_backward_compatible_no_model_specified(
        self,
    ) -> None:
        """structured_query() works without model (backward compatibility)."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "troller.worker.adapters.claude_client.Anthropic"
            ) as mock_anthropic_class:
                # Define test schema
                class TestSchema(BaseModel):
                    value: str

                # Mock Anthropic client response
                mock_anthropic = MagicMock()
                mock_anthropic_class.return_value = mock_anthropic
                mock_response = MagicMock()
                mock_response.content = [MagicMock(text='{"value": "test"}')]
                mock_anthropic.messages.create.return_value = mock_response

                # Create client without model
                client = ClaudeClient()
                result = await client.structured_query("Query", TestSchema)

                # Should still work and return valid result
                assert isinstance(result, TestSchema)
                assert result.value == "test"

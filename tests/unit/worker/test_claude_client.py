"""Unit tests for Claude API client adapter."""

import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from troller.worker.adapters.claude_client import ClaudeClient


class TestClaudeClientAnthropicProvider:
    """Test suite for ClaudeClient with Anthropic provider."""

    def test_init_stores_api_key_from_env(self) -> None:
        """ClaudeClient reads and stores ANTHROPIC_API_KEY when using anthropic provider."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "anthropic"
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                client = ClaudeClient()
                assert client._api_key == "test-key"
                assert client._anthropic_client is not None

    def test_init_raises_error_when_api_key_missing(self) -> None:
        """ClaudeClient raises clear error when ANTHROPIC_API_KEY is missing."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "anthropic"
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(
                    ValueError,
                    match="ANTHROPIC_API_KEY environment variable is required",
                ):
                    ClaudeClient()

    def test_init_accepts_optional_model_parameter(self) -> None:
        """ClaudeClient.__init__() accepts optional model parameter."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "anthropic"
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                client = ClaudeClient(model="claude-opus-4-5-20251101")
                assert client._model == "claude-opus-4-5-20251101"

    def test_init_stores_model_when_provided(self) -> None:
        """ClaudeClient.__init__() stores model correctly when provided."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "anthropic"
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                client = ClaudeClient(model="custom-model")
                assert hasattr(client, "_model")
                assert client._model == "custom-model"

    def test_init_defaults_model_to_none_when_not_provided(self) -> None:
        """ClaudeClient.__init__() defaults model to None when not provided."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "anthropic"
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                client = ClaudeClient()
                assert client._model is None

    @pytest.mark.asyncio
    async def test_query_yields_agent_sdk_messages(self) -> None:
        """query() yields messages from Agent SDK query."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "anthropic"
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
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "anthropic"
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
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "anthropic"
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
                    result = await client.structured_query(
                        "Generate test data", TestSchema
                    )

                    # Verify result is validated Pydantic model
                    assert isinstance(result, TestSchema)
                    assert result.summary == "Test summary"
                    assert result.count == 42

    @pytest.mark.asyncio
    async def test_structured_query_uses_json_schema(self) -> None:
        """structured_query() configures API with JSON schema validation."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "anthropic"
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
                    await client.structured_query(
                        "Query", TestSchema, model="test-model"
                    )

                    # Verify messages.create was called with schema
                    create_call = mock_anthropic.messages.create.call_args
                    assert create_call.kwargs["model"] == "test-model"
                    assert create_call.kwargs["max_tokens"] == 4096
                    assert "response_format" in create_call.kwargs["extra_body"]

                    # Verify schema configuration
                    response_format = create_call.kwargs["extra_body"][
                        "response_format"
                    ]
                    assert response_format["type"] == "json_schema"
                    assert response_format["json_schema"]["strict"] is True
                    assert "schema" in response_format["json_schema"]

    @pytest.mark.asyncio
    async def test_structured_query_defaults_to_sonnet_model(self) -> None:
        """structured_query() uses Sonnet 4.5 by default for anthropic provider."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "anthropic"
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
                    await client.structured_query(
                        "Query", TestSchema
                    )  # No model specified

                    # Verify default model
                    create_call = mock_anthropic.messages.create.call_args
                    assert create_call.kwargs["model"] == "claude-sonnet-4-5-20250929"

    @pytest.mark.asyncio
    async def test_structured_query_uses_instance_model_when_no_parameter(self) -> None:
        """structured_query() uses instance model when no model parameter provided."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "anthropic"
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
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "anthropic"
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


class TestClaudeClientBedrockProvider:
    """Test suite for ClaudeClient with Bedrock provider."""

    def test_init_does_not_require_api_key(self) -> None:
        """ClaudeClient does not require ANTHROPIC_API_KEY when using bedrock provider."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "bedrock"
            mock_config.llm_provider.bedrock_region = "us-west-2"
            with patch.dict(os.environ, {}, clear=True):
                with patch(
                    "troller.worker.adapters.claude_client.AnthropicBedrock"
                ) as mock_bedrock_class:
                    mock_bedrock_class.return_value = MagicMock()
                    client = ClaudeClient()
                    assert client._api_key is None
                    assert client._provider == "bedrock"

    def test_init_sets_bedrock_environment_variables(self) -> None:
        """ClaudeClient sets CLAUDE_CODE_USE_BEDROCK and AWS_REGION."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "bedrock"
            mock_config.llm_provider.bedrock_region = "us-east-1"
            with patch.dict(os.environ, {}, clear=True):
                with patch(
                    "troller.worker.adapters.claude_client.AnthropicBedrock"
                ) as mock_bedrock_class:
                    mock_bedrock_class.return_value = MagicMock()
                    ClaudeClient()
                    assert os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "1"
                    assert os.environ.get("AWS_REGION") == "us-east-1"

    def test_init_creates_bedrock_client(self) -> None:
        """ClaudeClient creates AnthropicBedrock client for bedrock provider."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "bedrock"
            mock_config.llm_provider.bedrock_region = "us-west-2"
            with patch.dict(os.environ, {}, clear=True):
                with patch(
                    "troller.worker.adapters.claude_client.AnthropicBedrock"
                ) as mock_bedrock_class:
                    mock_bedrock = MagicMock()
                    mock_bedrock_class.return_value = mock_bedrock
                    client = ClaudeClient()
                    mock_bedrock_class.assert_called_once_with(aws_region="us-west-2")
                    assert client._anthropic_client == mock_bedrock

    def test_model_conversion_to_bedrock_format(self) -> None:
        """ClaudeClient converts Anthropic model IDs to Bedrock format."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "bedrock"
            mock_config.llm_provider.bedrock_region = "us-west-2"
            with patch.dict(os.environ, {}, clear=True):
                with patch(
                    "troller.worker.adapters.claude_client.AnthropicBedrock"
                ) as mock_bedrock_class:
                    mock_bedrock_class.return_value = MagicMock()
                    client = ClaudeClient()

                    # Test conversion
                    result = client._to_bedrock_model_id("claude-opus-4-5-20251101")
                    assert result == "global.anthropic.claude-opus-4-5-20251101-v1:0"

    def test_model_already_in_bedrock_format_unchanged(self) -> None:
        """ClaudeClient does not modify models already in Bedrock format."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "bedrock"
            mock_config.llm_provider.bedrock_region = "us-west-2"
            with patch.dict(os.environ, {}, clear=True):
                with patch(
                    "troller.worker.adapters.claude_client.AnthropicBedrock"
                ) as mock_bedrock_class:
                    mock_bedrock_class.return_value = MagicMock()
                    client = ClaudeClient()

                    # Test with already-formatted model IDs
                    global_id = "global.anthropic.claude-opus-4-5-20251101-v1:0"
                    assert client._to_bedrock_model_id(global_id) == global_id

                    regional_id = "anthropic.claude-opus-4-5-20251101-v1:0"
                    assert client._to_bedrock_model_id(regional_id) == regional_id

    @pytest.mark.asyncio
    async def test_structured_query_converts_model_for_bedrock(self) -> None:
        """structured_query() converts model ID to Bedrock format."""
        with patch("troller.worker.adapters.claude_client.config") as mock_config:
            mock_config.llm_provider.provider = "bedrock"
            mock_config.llm_provider.bedrock_region = "us-west-2"
            with patch.dict(os.environ, {}, clear=True):
                with patch(
                    "troller.worker.adapters.claude_client.AnthropicBedrock"
                ) as mock_bedrock_class:
                    # Define test schema
                    class TestSchema(BaseModel):
                        value: str

                    # Mock Bedrock client response
                    mock_bedrock = MagicMock()
                    mock_bedrock_class.return_value = mock_bedrock
                    mock_response = MagicMock()
                    mock_response.content = [MagicMock(text='{"value": "test"}')]
                    mock_bedrock.messages.create.return_value = mock_response

                    client = ClaudeClient()
                    await client.structured_query("Query", TestSchema)

                    # Verify model was converted to Bedrock format
                    create_call = mock_bedrock.messages.create.call_args
                    assert (
                        create_call.kwargs["model"]
                        == "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
                    )

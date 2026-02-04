"""Unit tests for configuration management."""

import os
from unittest.mock import patch


from troller.config import ClaudeModelConfig, Config, LLMProviderConfig


class TestClaudeModelConfig:
    """Test suite for Claude model configuration."""

    def test_claude_model_config_loads_from_environment(self) -> None:
        """ClaudeModelConfig reads model settings from environment variables."""
        with patch.dict(
            os.environ,
            {
                "CLAUDE_PLANNING_MODEL": "claude-opus-test",
                "CLAUDE_CODING_MODEL": "claude-sonnet-test",
                "CLAUDE_REVIEW_MODEL": "claude-haiku-test",
            },
        ):
            config = ClaudeModelConfig()
            assert config.planning_model == "claude-opus-test"
            assert config.coding_model == "claude-sonnet-test"
            assert config.review_model == "claude-haiku-test"

    def test_claude_model_config_defaults_to_opus_for_planning(self) -> None:
        """ClaudeModelConfig defaults to Opus 4.5 for planning model."""
        with patch.dict(os.environ, {}, clear=True):
            config = ClaudeModelConfig()
            assert config.planning_model == "claude-opus-4-5-20251101"

    def test_claude_model_config_defaults_to_sonnet_for_coding(self) -> None:
        """ClaudeModelConfig defaults to Sonnet 4.5 for coding model."""
        with patch.dict(os.environ, {}, clear=True):
            config = ClaudeModelConfig()
            assert config.coding_model == "claude-sonnet-4-5-20250929"

    def test_claude_model_config_defaults_to_sonnet_for_review(self) -> None:
        """ClaudeModelConfig defaults to Sonnet 4.5 for review model."""
        with patch.dict(os.environ, {}, clear=True):
            config = ClaudeModelConfig()
            assert config.review_model == "claude-sonnet-4-5-20250929"

    def test_claude_model_config_allows_independent_configuration(self) -> None:
        """ClaudeModelConfig allows each model type to be configured independently."""
        with patch.dict(
            os.environ,
            {
                "CLAUDE_PLANNING_MODEL": "custom-planning",
                # Don't set CLAUDE_CODING_MODEL - should use default
                "CLAUDE_REVIEW_MODEL": "custom-review",
            },
        ):
            config = ClaudeModelConfig()
            assert config.planning_model == "custom-planning"
            assert config.coding_model == "claude-sonnet-4-5-20250929"  # default
            assert config.review_model == "custom-review"


class TestConfig:
    """Test suite for main application configuration."""

    def test_config_includes_claude_model_config(self) -> None:
        """Config includes claude field with ClaudeModelConfig."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            assert hasattr(config, "claude")
            assert isinstance(config.claude, ClaudeModelConfig)

    def test_config_claude_uses_environment_variables(self) -> None:
        """Config.claude respects CLAUDE_* environment variables."""
        with patch.dict(
            os.environ,
            {
                "CLAUDE_PLANNING_MODEL": "env-planning",
                "CLAUDE_CODING_MODEL": "env-coding",
                "CLAUDE_REVIEW_MODEL": "env-review",
            },
        ):
            config = Config()
            assert config.claude.planning_model == "env-planning"
            assert config.claude.coding_model == "env-coding"
            assert config.claude.review_model == "env-review"

    def test_config_includes_llm_provider_config(self) -> None:
        """Config includes llm_provider field with LLMProviderConfig."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            assert hasattr(config, "llm_provider")
            assert isinstance(config.llm_provider, LLMProviderConfig)


class TestLLMProviderConfig:
    """Test suite for LLM provider configuration."""

    def test_default_provider_is_bedrock(self) -> None:
        """LLMProviderConfig defaults to bedrock provider."""
        with patch.dict(os.environ, {}, clear=True):
            config = LLMProviderConfig()
            assert config.provider == "bedrock"

    def test_provider_can_be_set_to_anthropic(self) -> None:
        """LLMProviderConfig allows setting provider to anthropic."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic"}):
            config = LLMProviderConfig()
            assert config.provider == "anthropic"

    def test_default_bedrock_region(self) -> None:
        """LLMProviderConfig defaults bedrock_region to us-west-2."""
        with patch.dict(os.environ, {}, clear=True):
            config = LLMProviderConfig()
            assert config.bedrock_region == "us-west-2"

    def test_bedrock_region_from_environment(self) -> None:
        """LLMProviderConfig reads bedrock_region from LLM_BEDROCK_REGION."""
        with patch.dict(os.environ, {"LLM_BEDROCK_REGION": "us-east-1"}):
            config = LLMProviderConfig()
            assert config.bedrock_region == "us-east-1"

    def test_bedrock_profile_default_from_code(self) -> None:
        """LLMProviderConfig code default for bedrock_profile is None."""
        # Note: The default value is None, but .env files may override this
        # This test verifies the model field default, not runtime behavior
        fields = LLMProviderConfig.model_fields
        assert fields["bedrock_profile"].default is None

    def test_bedrock_profile_from_environment(self) -> None:
        """LLMProviderConfig reads bedrock_profile from LLM_BEDROCK_PROFILE."""
        with patch.dict(os.environ, {"LLM_BEDROCK_PROFILE": "my-profile"}):
            config = LLMProviderConfig()
            assert config.bedrock_profile == "my-profile"

    def test_full_bedrock_configuration(self) -> None:
        """LLMProviderConfig reads all bedrock settings together."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "bedrock",
                "LLM_BEDROCK_REGION": "eu-west-1",
                "LLM_BEDROCK_PROFILE": "production",
            },
        ):
            config = LLMProviderConfig()
            assert config.provider == "bedrock"
            assert config.bedrock_region == "eu-west-1"
            assert config.bedrock_profile == "production"

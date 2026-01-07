"""Configuration management for Troller.

Configuration is loaded from multiple sources with the following priority:
1. Command-line arguments (most specific)
2. Environment variables
3. .env file in project root
4. Default values defined here (least specific)
"""

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
# This ensures variables are available both for Pydantic settings and direct os.environ access
load_dotenv()


class ClaudeModelConfig(BaseSettings):
    """Claude AI model configuration.

    Attributes:
        planning_model: Model for planning agent (defaults to Opus 4.5).
        coding_model: Model for coding agent (defaults to Sonnet 4.5).
        review_model: Model for review agent (defaults to Sonnet 4.5).
    """

    model_config = SettingsConfigDict(
        env_prefix="CLAUDE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    planning_model: str = "claude-opus-4-5-20251101"
    coding_model: str = "claude-sonnet-4-5-20250929"
    review_model: str = "claude-sonnet-4-5-20250929"


class TemporalConfig(BaseSettings):
    """Temporal server configuration.

    Attributes:
        address: Temporal server address (host:port).
        task_queue: Task queue name for workflows and activities.
    """

    model_config = SettingsConfigDict(
        env_prefix="TEMPORAL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    address: str = "localhost:7233"
    task_queue: str = "troller-task-queue"


class GitHubConfig(BaseSettings):
    """GitHub API configuration.

    Attributes:
        token: GitHub personal access token (optional for public repos).
        api_url: Base URL for GitHub API.
    """

    model_config = SettingsConfigDict(
        env_prefix="GITHUB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    token: str | None = None
    api_url: str = "https://api.github.com"


class Config(BaseSettings):
    """Main application configuration.

    Attributes:
        temporal: Temporal server configuration.
        github: GitHub API configuration.
        claude: Claude AI model configuration.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    temporal: TemporalConfig = Field(default_factory=TemporalConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    claude: ClaudeModelConfig = Field(default_factory=ClaudeModelConfig)
    log_level: str = "INFO"


# Global configuration instance
config = Config()

"""Configuration management for Troller.

Configuration is loaded from multiple sources with the following priority:
1. Command-line arguments (most specific)
2. Environment variables
3. .env file in project root
4. Default values defined here (least specific)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


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
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    temporal: TemporalConfig = TemporalConfig()
    github: GitHubConfig = GitHubConfig()
    log_level: str = "INFO"


# Global configuration instance
config = Config()

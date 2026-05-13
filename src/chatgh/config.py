"""Typed environment configuration for ChatGH."""

from chatenv import BaseEnvConfig, EnvField


class GitHubConfig(BaseEnvConfig):
    """GitHub token configuration."""

    _title = "GitHub Configuration"
    _aliases = ["github", "gh"]
    _storage_dir = "GitHub"

    GITHUB_ACCESS_TOKEN = EnvField(
        "GITHUB_ACCESS_TOKEN",
        desc="GitHub Personal Access Token",
        is_sensitive=True,
    )


__all__ = ["GitHubConfig"]

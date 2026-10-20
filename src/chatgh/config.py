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

    @classmethod
    def test(cls) -> None:
        """Test exactly the typed profile already selected by ChatEnv."""
        import click

        from chatgh.github.token_status import check_token

        result = check_token(cls.GITHUB_ACCESS_TOKEN.value)
        failed = result["valid"] is not True
        warning = result["status"] == "expiring"
        color = "red" if failed else "yellow" if warning else "green"
        click.secho(f"GitHub token status: {result['status'].upper()}", fg=color)
        click.echo(f"Currently valid: {'yes' if result['valid'] is True else 'no' if result['valid'] is False else 'unknown'}")
        click.echo(f"Expires at (UTC): {result['expires_at'] or 'unknown'}")
        days = result["days_remaining"]
        click.echo(f"Days remaining: {days:.2f}" if days is not None else "Days remaining: unknown")
        prefix = "FAILED: " if failed else "WARNING: " if warning else ""
        click.secho(prefix + result["message"], fg=color)
        if failed:
            raise click.ClickException("GitHub token check failed.")


__all__ = ["GitHubConfig"]

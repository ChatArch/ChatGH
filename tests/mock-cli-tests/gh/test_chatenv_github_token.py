from unittest.mock import patch

import pytest
from click.testing import CliRunner

from chatgh.config import GitHubConfig


def test_real_chatenv_entry_selects_profile_and_preserves_active(tmp_path, monkeypatch):
    from chatenv.cli import cli
    from chatenv.store import EnvStore

    store = EnvStore(tmp_path / "envs")
    active = store.save_active(GitHubConfig, {"GITHUB_ACCESS_TOKEN": "synthetic-active-token"})
    store.save_profile(GitHubConfig, "work", {"GITHUB_ACCESS_TOKEN": "synthetic-work-token"})
    before = active.read_bytes()
    monkeypatch.setenv("GITHUB_ACCESS_TOKEN", "synthetic-process-token")
    payload = {"status": "valid", "valid": True, "expires_at": "2026-11-20T12:00:00Z", "days_remaining": 31, "http_status": 200, "message": "Token is currently valid."}
    old_value = GitHubConfig.GITHUB_ACCESS_TOKEN.value
    try:
        with patch("chatgh.github.token_status.check_token", return_value=payload) as check:
            for extra, selected in (([], "synthetic-active-token"), (["work"], "synthetic-work-token"), (["--profile", "work"], "synthetic-work-token")):
                result = CliRunner().invoke(cli, ["--home", str(tmp_path), "test", "-t", "gh", *extra, "-I"])
                assert result.exit_code == 0, result.output
                assert "Currently valid: yes" in result.output
                assert "2026-11-20T12:00:00Z" in result.output
                check.assert_called_with(selected)
        assert active.read_bytes() == before
    finally:
        GitHubConfig.GITHUB_ACCESS_TOKEN.value = old_value


def test_empty_named_profile_does_not_check_active_or_process_token(tmp_path, monkeypatch):
    from chatenv.cli import cli
    from chatenv.store import EnvStore

    store = EnvStore(tmp_path / "envs")
    store.save_active(GitHubConfig, {"GITHUB_ACCESS_TOKEN": "synthetic-active-token"})
    store.save_profile(GitHubConfig, "empty", {})
    monkeypatch.setenv("GITHUB_ACCESS_TOKEN", "synthetic-process-token")
    old_value = GitHubConfig.GITHUB_ACCESS_TOKEN.value
    try:
        with patch("requests.get") as get:
            result = CliRunner().invoke(cli, ["--home", str(tmp_path), "test", "-t", "gh", "--profile", "empty", "-I"])
        get.assert_not_called()
        assert result.exit_code == 1, result.output
        assert "GITHUB_ACCESS_TOKEN is not configured for this profile" in result.output
    finally:
        GitHubConfig.GITHUB_ACCESS_TOKEN.value = old_value


@pytest.mark.parametrize("status,valid,code", [("valid", True, 0), ("expiring", True, 0), ("invalid", False, 1), ("expired", False, 1), ("missing", False, 1), ("error", None, 1)])
def test_provider_renders_status_without_resolving_other_credentials(status, valid, code):
    import click

    @click.command()
    def command():
        GitHubConfig.test()

    token = "synthetic-selected-profile-token"
    old_value = GitHubConfig.GITHUB_ACCESS_TOKEN.value
    GitHubConfig.GITHUB_ACCESS_TOKEN.value = token
    payload = {"status": status, "valid": valid, "expires_at": "2026-10-25T12:00:00Z", "days_remaining": 5.25, "http_status": 200, "message": "Renew the token." if status == "expiring" else "Check details."}
    try:
        with patch("chatgh.github.token_status.check_token", return_value=payload) as check:
            result = CliRunner().invoke(command)
        check.assert_called_once_with(token)
    finally:
        GitHubConfig.GITHUB_ACCESS_TOKEN.value = old_value
    assert result.exit_code == code, result.output
    assert "2026-10-25T12:00:00Z" in result.output
    assert "5.25" in result.output
    assert token not in result.output
    if status == "expiring":
        assert "WARNING" in result.output
    elif status in ("invalid", "expired", "missing", "error"):
        assert "FAILED" in result.output


def test_unknown_expiration_output():
    import click

    @click.command()
    def command():
        GitHubConfig.test()

    payload = {"status": "valid", "valid": True, "expires_at": None, "days_remaining": None, "http_status": 200, "message": "Expiration is unknown."}
    with patch("chatgh.github.token_status.check_token", return_value=payload):
        result = CliRunner().invoke(command)
    assert result.exit_code == 0
    assert "Expires at (UTC): unknown" in result.output
    assert "Days remaining: unknown" in result.output

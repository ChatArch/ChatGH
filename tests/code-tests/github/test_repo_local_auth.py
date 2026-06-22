import base64
from types import SimpleNamespace

import chatgh.github.api as gh_api


def _basic_header(token: str) -> str:
    encoded = base64.b64encode(("x-access-token:" + token).encode()).decode()
    return f"Authorization: Basic {encoded}"


def test_reads_repo_local_extraheader_from_git_config(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        assert args == [
            "git",
            "config",
            "--local",
            "--get",
            "http.https://github.com/ChatArch/ChatShare.git.extraHeader",
        ]
        return SimpleNamespace(returncode=0, stdout=_basic_header("repo-token") + "\n", stderr="")

    monkeypatch.setattr(gh_api.subprocess, "run", fake_run)

    token = gh_api.read_github_token_from_git(
        {"protocol": "https", "host": "github.com", "path": "ChatArch/ChatShare"}
    )

    assert token == "repo-token"
    assert calls


def test_configure_github_https_token_writes_repo_local_git_config(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(gh_api.subprocess, "run", fake_run)

    gh_api.configure_github_https_token(
        {"protocol": "https", "host": "github.com", "path": "ChatArch/ChatShare"},
        "repo-token",
    )

    assert calls == [
        [
            "git",
            "config",
            "--local",
            "http.https://github.com/ChatArch/ChatShare.git.extraHeader",
            _basic_header("repo-token"),
        ]
    ]
    assert all("--global" not in call for call in calls)
    assert all("credential" not in call for call in calls)


def test_resolve_token_prefers_repo_local_git_config_over_chatenv(monkeypatch):
    monkeypatch.setattr(gh_api, "read_github_token_from_git", lambda *args, **kwargs: "repo-token")
    monkeypatch.setattr(gh_api, "get_github_config_token", lambda: "fallback-token")

    info = gh_api.resolve_token_with_source(
        None,
        credential_path={"protocol": "https", "host": "github.com", "path": "ChatArch/ChatShare"},
    )

    assert info == {"token": "repo-token", "source": "repo git config"}

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
            "--get-all",
            "http.https://github.com/ChatArch/ChatShare.git.extraHeader",
        ]
        return SimpleNamespace(returncode=0, stdout=_basic_header("repo-token") + "\n", stderr="")

    monkeypatch.setattr(gh_api.subprocess, "run", fake_run)

    token = gh_api.read_github_token_from_git(
        {"protocol": "https", "host": "github.com", "path": "ChatArch/ChatShare"}
    )

    assert token == "repo-token"
    assert calls


def test_reads_legacy_no_dot_git_repo_local_extraheader(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[-1].endswith(".git.extraHeader"):
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout=_basic_header("legacy-token") + "\n", stderr="")

    monkeypatch.setattr(gh_api.subprocess, "run", fake_run)

    token = gh_api.read_github_token_from_git(
        {"protocol": "https", "host": "github.com", "path": "ChatArch/ChatShare"}
    )

    assert token == "legacy-token"
    assert [call[-1] for call in calls] == [
        "http.https://github.com/ChatArch/ChatShare.git.extraHeader",
        "http.https://github.com/ChatArch/ChatShare.extraHeader",
    ]


def test_reads_a_token_header_even_when_an_unrelated_header_shares_the_key(monkeypatch):
    def fake_run(args, **kwargs):
        assert args == [
            "git",
            "config",
            "--local",
            "--get-all",
            "http.https://github.com/ChatArch/ChatShare.git.extraHeader",
        ]
        return SimpleNamespace(
            returncode=0,
            stdout="X-Trace: keep\n" + _basic_header("repo-token") + "\n",
            stderr="",
        )

    monkeypatch.setattr(gh_api.subprocess, "run", fake_run)

    token = gh_api.read_github_token_from_git(
        {"protocol": "https", "host": "github.com", "path": "ChatArch/ChatShare"}
    )

    assert token == "repo-token"


def test_configure_github_https_token_writes_repo_local_git_config(tmp_path, monkeypatch):
    import subprocess
    calls = []
    original = subprocess.run
    repo = tmp_path / "repo"
    original(["git", "init", "-q", str(repo)], check=True)
    original(["git", "-C", str(repo), "remote", "add", "origin", "https://github.com/ChatArch/ChatShare.git"], check=True)
    original(["git", "-C", str(repo), "config", "review.keep", "untouched"], check=True)
    monkeypatch.chdir(repo)

    def tracked_run(args, **kwargs):
        calls.append(args)
        return original(args, **kwargs)

    monkeypatch.setattr(gh_api.subprocess, "run", tracked_run)
    credential = {"protocol": "https", "host": "github.com", "path": "ChatArch/ChatShare"}
    gh_api.configure_github_https_token(credential, "repo-token")
    assert gh_api.read_github_token_from_git(credential) == "repo-token"
    assert original(["git", "config", "--get", "review.keep"], check=True, capture_output=True, text=True).stdout.strip() == "untouched"
    assert all("repo-token" not in str(call) and _basic_header("repo-token") not in str(call) for call in calls)
    assert all("--global" not in call for call in calls)


def test_resolve_token_prefers_repo_local_git_config_over_chatenv(monkeypatch):
    monkeypatch.setattr(gh_api, "read_github_token_from_git", lambda *args, **kwargs: "repo-token")
    monkeypatch.setattr(gh_api, "get_github_config_token", lambda: "fallback-token")

    info = gh_api.resolve_token_with_source(
        None,
        credential_path={"protocol": "https", "host": "github.com", "path": "ChatArch/ChatShare"},
    )

    assert info == {"token": "repo-token", "source": "repo git config"}

"""Regression coverage for invocation-scoped Git transport."""

from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from chatgh.github import transport


def _header(token: str) -> str:
    encoded = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")
    return f"Authorization: Basic {encoded}"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


@pytest.fixture
def github_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = tmp_path / "repo"
    _git(tmp_path, "init", "-q", str(repo))
    _git(repo, "checkout", "-q", "-b", "main")
    _git(repo, "config", "user.email", "transport@example.invalid")
    _git(repo, "config", "user.name", "Transport Test")
    (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-qm", "fixture")
    _git(repo, "remote", "add", "origin", "https://github.com/acme/fetch.git")
    _git(repo, "config", "branch.main.remote", "origin")
    _git(repo, "config", "branch.main.merge", "refs/heads/main")
    monkeypatch.chdir(repo)
    return repo


def _token_info(token: str) -> dict[str, str]:
    return {"token": token, "source": "GitHubConfig.GITHUB_ACCESS_TOKEN"}


def test_fetch_defaults_to_current_branch_upstream_and_uses_matching_pin(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[list[str], object, str]] = []

    def fake_resolve(token, credential_path=None, exact_only=False, cwd=None):
        assert token is None
        assert cwd == str(github_repo)
        assert credential_path == {
            "protocol": "https",
            "host": "github.com",
            "path": "acme/fetch",
        }
        return {"token": "repo-pin", "source": "repo git config"}

    def fake_run(args, destination, token, *, cwd=None):
        calls.append((args, destination, token))
        return SimpleNamespace(returncode=0, stdout="fetched", stderr="")

    monkeypatch.setattr(transport, "resolve_token_with_source", fake_resolve)
    monkeypatch.setattr(transport, "_run_authenticated_git", fake_run)

    payload = transport.fetch(cwd=str(github_repo))

    assert calls[0][0] == ["fetch", "--recurse-submodules=no", "origin"]
    assert calls[0][2] == "repo-pin"
    assert payload["remote"] == "origin"
    assert payload["token_source"] == "repo git config"


def test_fetch_fails_closed_without_an_upstream_or_explicit_remote(
    github_repo: Path,
) -> None:
    _git(github_repo, "config", "--unset", "branch.main.remote")

    with pytest.raises(Exception, match="upstream.*REMOTE"):
        transport.fetch(cwd=str(github_repo))


def test_pull_is_fast_forward_only_by_default_and_rebase_is_explicit(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authenticated: list[list[str]] = []
    local: list[list[str]] = []
    monkeypatch.setattr(transport, "resolve_token_with_source", lambda *args, **kwargs: _token_info("token"))
    monkeypatch.setattr(
        transport,
        "_run_authenticated_git",
        lambda args, destination, token, *, cwd=None: authenticated.append(args)
        or SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        transport,
        "_run_local_git",
        lambda args, *, cwd=None: local.append(args)
        or SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    transport.pull(cwd=str(github_repo))
    transport.pull(rebase=True, cwd=str(github_repo))

    assert authenticated == [
        ["fetch", "--recurse-submodules=no", "origin", "main"],
        ["fetch", "--recurse-submodules=no", "origin", "main"],
    ]
    assert local == [["merge", "--ff-only", "FETCH_HEAD"], ["rebase", "FETCH_HEAD"]]


def test_push_uses_effective_pushurl_and_safe_explicit_flags(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(github_repo, "remote", "set-url", "--push", "origin", "https://github.com/acme/push.git")
    calls: list[tuple[list[str], object, str]] = []
    monkeypatch.setattr(transport, "resolve_token_with_source", lambda *args, **kwargs: _token_info("token"))
    monkeypatch.setattr(
        transport,
        "_run_authenticated_git",
        lambda args, destination, token, *, cwd=None: calls.append((args, destination, token))
        or SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    payload = transport.push(
        "origin",
        "main:main",
        set_upstream=True,
        dry_run=True,
        cwd=str(github_repo),
    )

    assert calls[0][0] == ["push", "--recurse-submodules=no", "--set-upstream", "--dry-run", "origin", "main:main"]
    assert calls[0][1].credential_path["path"] == "acme/push"
    assert payload["dry_run"] is True


def test_https_clone_uses_transport_helper_not_a_token_in_git_arguments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authenticated: list[tuple[list[str], str]] = []
    local: list[tuple[list[str], str | None]] = []
    monkeypatch.setattr(transport, "resolve_token_with_source", lambda *args, **kwargs: _token_info("clone-token"))
    monkeypatch.setattr(
        transport,
        "_run_authenticated_git",
        lambda args, destination, token, *, cwd=None: authenticated.append((args, token))
        or SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        transport,
        "_run_local_git",
        lambda args, *, cwd=None: local.append((args, cwd))
        or SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    payload = transport.clone_repository("acme/private", "private", cwd=str(tmp_path))

    command, resolved_token = authenticated[0]
    assert command == [
        "clone",
        "--no-checkout",
        "--no-recurse-submodules",
        "--",
        "https://github.com/acme/private.git",
        "private",
    ]
    assert "clone-token" not in " ".join(command)
    assert resolved_token == "clone-token"
    assert local == [(["checkout"], str(tmp_path / "private"))]
    assert payload["token_source"] == "GitHubConfig.GITHUB_ACCESS_TOKEN"


@pytest.mark.parametrize(
    "value",
    [
        "-c",
        "+main:main",
        "main\n--upload-pack=evil",
        ":main",
        "main:",
        "main.lock",
        "main/",
        "main/.hidden",
    ],
)
def test_transport_rejects_flag_and_force_injection(value: str) -> None:
    with pytest.raises(Exception):
        transport.validate_refspec(value)


@pytest.mark.parametrize(
    "value",
    ["../repo", "owner/..", "https://github.com/../repo.git", "https://github.com/owner/.."],
)
def test_transport_rejects_traversal_like_repository_paths(value: str) -> None:
    with pytest.raises(Exception):
        if value.startswith("https://"):
            transport.validate_github_https_url(value)
        else:
            transport.destination_from_repo(value)


def test_clone_validates_effective_url_rewrite_before_resolving_a_token(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(
        github_repo,
        "config",
        "url.ssh://git@evil.invalid/.insteadOf",
        "https://github.com/acme/private.git",
    )
    resolved: list[bool] = []
    monkeypatch.setattr(
        transport,
        "resolve_token_with_source",
        lambda *args, **kwargs: resolved.append(True) or _token_info("must-not-resolve"),
    )
    monkeypatch.setattr(
        transport,
        "_run_authenticated_git",
        lambda *args, **kwargs: pytest.fail("clone must reject the rewritten URL before running Git"),
    )

    with pytest.raises(Exception, match="github.com HTTPS"):
        transport.clone_repository("acme/private", "private", cwd=str(github_repo))

    assert resolved == []


def test_clone_resolves_a_github_rewrite_before_looking_up_its_pin(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(
        github_repo,
        "config",
        "url.https://github.com/renamed/.insteadOf",
        "https://github.com/acme/",
    )
    seen: list[dict[str, str]] = []
    monkeypatch.setattr(
        transport,
        "resolve_token_with_source",
        lambda token, credential_path=None, **kwargs: seen.append(credential_path)
        or _token_info("rewritten-pin"),
    )
    monkeypatch.setattr(
        transport,
        "_run_authenticated_git",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        transport,
        "_run_local_git",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    payload = transport.clone_repository("acme/private", "private", cwd=str(github_repo))

    assert seen == [{"protocol": "https", "host": "github.com", "path": "renamed/private"}]
    assert payload["repo"] == "renamed/private"


def test_effective_urls_reject_non_github_rewrites_and_multiple_pushurls(
    github_repo: Path,
) -> None:
    _git(github_repo, "config", "url.https://example.invalid/.insteadOf", "https://github.com/acme/fetch.git")
    with pytest.raises(Exception, match="github.com HTTPS"):
        transport.destination_for_remote("origin", "fetch", cwd=str(github_repo))

    _git(github_repo, "config", "--unset-all", "url.https://example.invalid/.insteadOf")
    _git(github_repo, "remote", "set-url", "--push", "origin", "https://github.com/acme/first.git")
    _git(github_repo, "remote", "set-url", "--add", "--push", "origin", "https://github.com/acme/second.git")
    with pytest.raises(Exception, match="multiple push URLs"):
        transport.destination_for_remote("origin", "push", cwd=str(github_repo))


def test_transport_uses_cwd_not_git_dir_override_for_target_and_matching_pin(
    github_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(github_repo, "config", "http.https://github.com/acme/fetch.git.extraHeader", _header("repo-pin"))
    unrelated = tmp_path / "unrelated"
    _git(tmp_path, "init", "-q", str(unrelated))
    monkeypatch.setenv("GIT_DIR", str(unrelated / ".git"))
    calls: list[str | None] = []
    monkeypatch.setattr(
        transport,
        "_run_authenticated_git",
        lambda args, destination, token, *, cwd=None: calls.append(token)
        or SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    payload = transport.fetch(cwd=str(github_repo))

    assert payload["repo"] == "acme/fetch"
    assert calls == ["repo-pin"]


def test_child_environment_strips_repository_override_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_EXEC_PATH",
    ):
        monkeypatch.setenv(key, "unsafe")

    env = transport._without_unsafe_environment()

    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_EXEC_PATH",
    ):
        assert key not in env


def test_child_environment_keeps_github_tokens_only_in_the_scoped_helper(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for key in ("GITHUB_ACCESS_TOKEN", "GITHUB_TOKEN", "GH_TOKEN", "GH_ENTERPRISE_TOKEN"):
        monkeypatch.setenv(key, "ambient-token")
    destination = transport.destination_for_remote("origin", "fetch", cwd=str(github_repo))

    env = transport.build_transport_env("scoped-token", destination, cwd=str(github_repo))

    for key in ("GITHUB_ACCESS_TOKEN", "GITHUB_TOKEN", "GH_TOKEN", "GH_ENTERPRISE_TOKEN"):
        assert key not in env
    assert env[transport.TOKEN_ENV] == "scoped-token"


def test_transport_rejects_an_auth_config_key_it_cannot_safely_reset(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = transport.destination_for_remote("origin", "fetch", cwd=str(github_repo))
    monkeypatch.setattr(
        transport,
        "_effective_config_names",
        lambda **kwargs: ["http.bad key.extraHeader"],
    )

    with pytest.raises(Exception, match="inherited HTTP or credential configuration"):
        transport.build_transport_env("new-token", destination, cwd=str(github_repo))


def test_child_env_resets_inherited_headers_and_helpers_without_token_in_config(
    github_repo: Path,
) -> None:
    _git(github_repo, "config", "--add", "http.extraHeader", _header("old-generic"))
    _git(
        github_repo,
        "config",
        "--add",
        "http.https://github.com/acme/fetch.git.extraHeader",
        _header("old-scoped"),
    )
    _git(github_repo, "config", "credential.helper", "store")
    destination = transport.destination_for_remote("origin", "fetch", cwd=str(github_repo))

    env = transport.build_transport_env("new-token", destination, cwd=str(github_repo))
    count = int(env["GIT_CONFIG_COUNT"])
    pairs = {
        env[f"GIT_CONFIG_KEY_{index}"].lower(): env[f"GIT_CONFIG_VALUE_{index}"]
        for index in range(count)
    }

    assert pairs["http.extraheader"] == ""
    assert pairs["http.https://github.com/acme/fetch.git.extraheader"] == ""
    assert pairs["credential.helper"] == ""
    assert pairs["http.followredirects"] == "false"
    assert pairs["core.hookspath"] == os.devnull
    assert pairs["submodule.recurse"] == "false"
    assert "new-token" not in "\n".join(pairs.values())
    assert env[transport.TOKEN_ENV] == "new-token"
    assert "GIT_TRACE" not in env


def test_child_config_effectively_clears_old_headers_and_uses_only_its_helper(
    github_repo: Path,
) -> None:
    _git(github_repo, "config", "http.extraHeader", _header("old-generic"))
    _git(
        github_repo,
        "config",
        "http.https://github.com/acme/fetch.git.extraHeader",
        _header("old-scoped"),
    )
    _git(github_repo, "config", "credential.helper", "store")
    _git(github_repo, "config", "credential.https://github.com.useHttpPath", "false")
    _git(
        github_repo,
        "config",
        "http.https://github.com/acme/fetch.git/info.followRedirects",
        "true",
    )
    destination = transport.destination_for_remote("origin", "fetch", cwd=str(github_repo))
    env = transport.build_transport_env("scoped-token", destination, cwd=str(github_repo))

    headers = subprocess.run(
        ["git", "-C", str(github_repo), "config", "--get-urlmatch", "http.extraHeader", destination.url],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    credential = subprocess.run(
        ["git", "-C", str(github_repo), "credential", "fill"],
        input="protocol=https\nhost=github.com\npath=acme/fetch.git\n\n",
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    redirect = subprocess.run(
        [
            "git",
            "-C",
            str(github_repo),
            "config",
            "--get-urlmatch",
            "http.followRedirects",
            destination.url + "/info/refs",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    use_http_path = subprocess.run(
        [
            "git",
            "-C",
            str(github_repo),
            "config",
            "--get-urlmatch",
            "credential.useHttpPath",
            destination.url,
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert headers.returncode == 0
    assert headers.stdout.strip() == ""
    assert "old-generic" not in headers.stdout
    assert "old-scoped" not in headers.stdout
    assert credential.returncode == 0, credential.stderr
    assert "password=scoped-token" in credential.stdout
    assert redirect.stdout.strip() == "false"
    assert use_http_path.stdout.strip() == "true"


def test_configured_upstream_branch_injection_is_rejected_before_token_resolution(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(github_repo, "config", "branch.main.merge", "-cunsafe")
    resolved = []
    monkeypatch.setattr(
        transport,
        "resolve_token_with_source",
        lambda *args, **kwargs: resolved.append(True) or _token_info("should-not-resolve"),
    )

    with pytest.raises(Exception, match="refs/heads"):
        transport.fetch(cwd=str(github_repo))

    assert not resolved


def test_credential_helper_only_answers_exact_get_requests() -> None:
    env = {
        transport.TOKEN_ENV: "helper-token",
        transport.PROTOCOL_ENV: "https",
        transport.HOST_ENV: "github.com",
        transport.PATH_ENV: "acme/repo.git",
    }

    accepted = transport.credential_helper_response(
        "get", "protocol=https\nhost=github.com\npath=acme/repo.git\n\n", env=env
    )
    rejected = transport.credential_helper_response(
        "get", "protocol=https\nhost=github.com\npath=acme/other.git\n\n", env=env
    )

    assert "password=helper-token" in accepted
    assert rejected == ""
    assert transport.credential_helper_response("store", "", env=env) == ""
    assert transport.credential_helper_response("erase", "", env=env) == ""
    assert (
        transport.credential_helper_response(
            "get", "protocol=https\nhost=github.com\npath=acme/repo.git\x00other\n\n", env=env
        )
        == ""
    )


def test_isolated_chatenv_rotation_is_resolved_per_invocation_without_repo_config_mutation(
    github_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import chatgh.github.api as gh_api

    isolated_envs = tmp_path / "isolated-chatenv"
    monkeypatch.setattr(gh_api, "CHATARCH_ENV_DIR", isolated_envs)
    gh_api.save_github_token_to_env("profile-a")
    seen: list[str] = []
    before = _git(github_repo, "config", "--local", "--list")
    monkeypatch.setattr(
        transport,
        "_run_authenticated_git",
        lambda args, destination, token, *, cwd=None: seen.append(token)
        or SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    transport.fetch("origin", cwd=str(github_repo))
    gh_api.save_github_token_to_env("profile-b")
    transport.fetch("origin", cwd=str(github_repo))

    assert seen == ["profile-a", "profile-b"]
    assert _git(github_repo, "config", "--local", "--list") == before


def test_unset_token_removes_only_local_github_token_headers(
    github_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected = _header("selected")
    legacy = _header("legacy")
    other_host = _header("other-host")
    foreign = tmp_path / "foreign.config"
    foreign.write_text(
        '[http "https://github.com/foreign/repo.git"]\n\textraHeader = ' + _header("foreign") + "\n",
        encoding="utf-8",
    )
    _git(github_repo, "config", "--add", "http.https://github.com/acme/fetch.git.extraHeader", selected)
    _git(github_repo, "config", "--add", "http.https://github.com/acme/fetch.extraHeader", legacy)
    _git(github_repo, "config", "--add", "http.https://example.invalid/acme/fetch.git.extraHeader", other_host)
    _git(github_repo, "config", "include.path", str(foreign))
    monkeypatch.setattr(transport, "resolve_token_with_source", lambda *args, **kwargs: {"token": None, "source": "none"})

    result = transport.unset_token(cwd=str(github_repo))

    local = _git(github_repo, "config", "--local", "--list")
    assert result == {
        "repo": "acme/fetch",
        "removed_keys": [
            "http.https://github.com/acme/fetch.git.extraHeader",
            "http.https://github.com/acme/fetch.extraHeader",
        ],
        "removed_count": 2,
        "default_resolves": False,
    }
    assert selected not in local
    assert legacy not in local
    assert other_host in local
    assert _header("foreign") in foreign.read_text(encoding="utf-8")


@pytest.mark.parametrize("operation", ["fetch", "pull", "push"])
def test_transport_rejects_remote_vcs_before_resolving_credentials(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    _git(github_repo, "config", "remote.origin.vcs", "custom-review-canary")
    resolved = []
    monkeypatch.setattr(
        transport, "resolve_token_with_source",
        lambda *args, **kwargs: resolved.append(True) or _token_info("dummy-token"),
    )
    monkeypatch.setattr(
        transport, "_run_authenticated_git",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        transport, "_run_local_git",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    with pytest.raises(Exception, match="custom Git program"):
        getattr(transport, operation)(cwd=str(github_repo))
    assert not resolved


def test_unset_token_locks_before_read_modify_write(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(github_repo, "config", "http.https://github.com/acme/fetch.git.extraHeader", _header("dummy-pin"))
    _git(github_repo, "config", "review.existing", "preserve-me")
    original_parse = transport._parse_local_header_removals
    writers = []

    def attempt_concurrent_writer(content, selected, all_tokens):
        writers.append(subprocess.run(
            ["git", "-C", str(github_repo), "config", "--local", "review.concurrent", "keep-me"],
            capture_output=True, text=True,
        ))
        return original_parse(content, selected, all_tokens)

    monkeypatch.setattr(transport, "_parse_local_header_removals", attempt_concurrent_writer)
    monkeypatch.setattr(transport, "resolve_token_with_source", lambda *a, **kw: {"token": None, "source": "none"})
    result = transport.unset_token(cwd=str(github_repo))
    assert result["removed_count"] == 1
    assert len(writers) == 1
    assert writers[0].returncode != 0
    assert "lock" in writers[0].stderr.lower()
    assert _git(github_repo, "config", "--local", "--get", "review.existing").strip() == "preserve-me"
    assert not (github_repo / ".git" / "config.lock").exists()


def test_unset_token_all_is_idempotent_and_preserves_non_token_headers(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(github_repo, "config", "--add", "http.https://github.com/acme/other.git.extraHeader", _header("other"))
    _git(github_repo, "config", "--add", "http.https://github.com/acme/other.git.extraHeader", "X-Test: keep")
    monkeypatch.setattr(transport, "resolve_token_with_source", lambda *args, **kwargs: {"token": None, "source": "none"})

    first = transport.unset_token(all_tokens=True, cwd=str(github_repo))
    second = transport.unset_token(all_tokens=True, cwd=str(github_repo))

    local = _git(github_repo, "config", "--local", "--list")
    assert first["removed_count"] == 1
    assert second["removed_count"] == 0
    assert "X-Test: keep" in local


def test_unset_token_can_clear_a_legacy_pin_for_a_github_ssh_remote(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(github_repo, "remote", "set-url", "origin", "git@github.com:acme/fetch.git")
    legacy = _header("legacy-ssh-pin")
    _git(github_repo, "config", "http.https://github.com/acme/fetch.extraHeader", legacy)
    monkeypatch.setattr(transport, "resolve_token_with_source", lambda *args, **kwargs: {"token": None, "source": "none"})

    result = transport.unset_token(cwd=str(github_repo))

    assert result["repo"] == "acme/fetch"
    assert result["removed_count"] == 1
    assert legacy not in _git(github_repo, "config", "--local", "--list")


def test_unset_token_fails_closed_without_a_selected_remote(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _git(github_repo, "config", "--unset", "branch.main.remote")
    _git(github_repo, "remote", "remove", "origin")
    _git(github_repo, "remote", "add", "alpha", "https://github.com/acme/alpha.git")
    _git(github_repo, "remote", "add", "beta", "https://github.com/acme/beta.git")
    alpha_header = _header("alpha")
    beta_header = _header("beta")
    _git(github_repo, "config", "http.https://github.com/acme/alpha.git.extraHeader", alpha_header)
    _git(github_repo, "config", "http.https://github.com/acme/beta.git.extraHeader", beta_header)
    monkeypatch.setattr(transport, "resolve_token_with_source", lambda *args, **kwargs: pytest.fail("no resolver"))

    with pytest.raises(Exception, match="selected GitHub remote"):
        transport.unset_token(cwd=str(github_repo))

    local = _git(github_repo, "config", "--local", "--list")
    assert alpha_header in local
    assert beta_header in local


def test_unset_token_fails_without_writing_when_local_config_is_locked(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    header = _header("locked")
    _git(github_repo, "config", "http.https://github.com/acme/fetch.git.extraHeader", header)
    config_path = Path(_git(github_repo, "rev-parse", "--git-path", "config").strip())
    if not config_path.is_absolute():
        config_path = github_repo / config_path
    lock_path = config_path.with_name(config_path.name + ".lock")
    lock_path.write_text("other git writer\n", encoding="utf-8")
    monkeypatch.setattr(transport, "resolve_token_with_source", lambda *args, **kwargs: {"token": None, "source": "none"})

    with pytest.raises(Exception, match="local Git config safely"):
        transport.unset_token(cwd=str(github_repo))

    assert header in _git(github_repo, "config", "--local", "--list")
    assert lock_path.read_text(encoding="utf-8") == "other git writer\n"


def test_git_exit_status_is_preserved_and_secret_is_redacted(
    github_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = transport.destination_for_remote("origin", "fetch", cwd=str(github_repo))

    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=17, stdout="token-123", stderr="Authorization: Basic token-123")

    monkeypatch.setattr(transport.subprocess, "run", fake_run)
    monkeypatch.setattr(transport, "build_transport_env", lambda *args, **kwargs: {})
    with pytest.raises(transport.GitTransportError) as excinfo:
        transport._run_authenticated_git(["fetch", "origin"], destination, "token-123", cwd=str(github_repo))

    assert excinfo.value.exit_code == 17
    assert "token-123" not in str(excinfo.value)

"""Invocation-scoped, HTTPS-only Git transport for GitHub remotes.

The public functions in this module deliberately accept a small, auditable
command surface.  They validate a remote before resolving a token and pass
credentials to Git only through a one-shot credential helper configured for
that child process.
"""

from __future__ import annotations

import base64
import os
import re
import shlex
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional
from urllib.parse import urlsplit

import click

from chatgh.github.api import CredentialQuery, resolve_token_with_source


TOKEN_ENV = "CHATGH_TRANSPORT_TOKEN"
PROTOCOL_ENV = "CHATGH_TRANSPORT_PROTOCOL"
HOST_ENV = "CHATGH_TRANSPORT_HOST"
PATH_ENV = "CHATGH_TRANSPORT_PATH"

_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_REMOTE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
_REPO_PART_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_CONFIG_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@%?&=+~\\-]*$")
_SECTION_RE = re.compile(
    r'^\s*\[\s*http\s+"(?P<url>(?:[^"\\]|\\.)*)"\s*\]\s*(?:[#;].*)?$',
    re.IGNORECASE,
)
_EXTRAHEADER_RE = re.compile(r"^\s*extraheader\s*(?:=|\s)\s*(?P<value>.*?)\s*(?:\r?\n)?$", re.IGNORECASE)
_GIT_REPOSITORY_OVERRIDE_ENV = {
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_INDEX_FILE",
    "GIT_INDEX_VERSION",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_GRAFT_FILE",
    "GIT_REPLACE_REF_BASE",
    "GIT_NAMESPACE",
    "GIT_SHALLOW_FILE",
    "GIT_CEILING_DIRECTORIES",
    "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_EXEC_PATH",
}
_AMBIENT_GITHUB_TOKEN_ENV = {
    "GITHUB_ACCESS_TOKEN",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GH_ENTERPRISE_TOKEN",
}


@dataclass(frozen=True)
class GitDestination:
    """A validated GitHub HTTPS endpoint and its credential lookup path."""

    url: str
    credential_path: CredentialQuery
    request_path: str

    @property
    def repo(self) -> str:
        return self.credential_path["path"]


class GitTransportError(click.ClickException):
    """A redacted Git failure that preserves Git's meaningful exit status."""

    def __init__(self, message: str, returncode: int = 1):
        super().__init__(message)
        self.exit_code = returncode if 1 <= returncode <= 255 else 1


@dataclass(frozen=True)
class _GitResult:
    returncode: int
    stdout: str
    stderr: str


def _contains_control(value: str) -> bool:
    return bool(_CONTROL_RE.search(value))


def _require_safe_text(value: Optional[str], label: str) -> str:
    candidate = (value or "").strip()
    if not candidate or _contains_control(candidate):
        raise click.ClickException(f"{label} must be a non-empty value without control characters.")
    return candidate


def validate_remote_name(remote: str) -> str:
    candidate = _require_safe_text(remote, "Remote")
    if not _REMOTE_RE.fullmatch(candidate) or candidate.startswith("-"):
        raise click.ClickException("Remote must be a configured Git remote name, not a Git option.")
    return candidate


def _is_safe_refname(candidate: str) -> bool:
    """Apply the Git refname constraints relevant to our narrow argument surface."""

    if candidate == "@" or candidate.endswith(".") or candidate.endswith(".lock"):
        return False
    components = candidate.split("/")
    return all(
        component
        and not component.startswith(".")
        and not component.endswith(".")
        and not component.endswith(".lock")
        for component in components
    )


def validate_branch(branch: str) -> str:
    candidate = _require_safe_text(branch, "Branch")
    if (
        not _REF_RE.fullmatch(candidate)
        or candidate.startswith("-")
        or ".." in candidate
        or not _is_safe_refname(candidate)
    ):
        raise click.ClickException("Branch must be a safe branch name, not a Git option.")
    return candidate


def validate_refspec(refspec: str) -> str:
    candidate = _require_safe_text(refspec, "Refspec")
    if candidate.startswith(("-", "+")) or any(char.isspace() for char in candidate):
        raise click.ClickException("Refspec must not contain Git options or force-push syntax.")
    if candidate.count(":") > 1 or candidate == ":" or ".." in candidate:
        raise click.ClickException("Refspec is not a supported safe Git refspec.")
    parts = candidate.split(":")
    if any(not part for part in parts):
        raise click.ClickException("Refspec must name both sides when using ':'.")
    for part in parts:
        if (
            not _REF_RE.fullmatch(part)
            or part.startswith("-")
            or not _is_safe_refname(part)
        ):
            raise click.ClickException("Refspec is not a supported safe Git refspec.")
    return candidate


def _destination_from_parts(owner: str, name: str, *, suffix: str = ".git") -> GitDestination:
    if (
        not _REPO_PART_RE.fullmatch(owner)
        or not _REPO_PART_RE.fullmatch(name)
        or owner in {".", ".."}
        or name in {".", ".."}
    ):
        raise click.ClickException("GitHub destination must use an owner/name repository path.")
    request_path = f"{owner}/{name}{suffix}"
    return GitDestination(
        url=f"https://github.com/{request_path}",
        credential_path={"protocol": "https", "host": "github.com", "path": f"{owner}/{name}"},
        request_path=request_path,
    )


def destination_from_repo(repo: str) -> GitDestination:
    candidate = _require_safe_text(repo, "Repository")
    if candidate.endswith(".git"):
        candidate = candidate[:-4]
    parts = candidate.split("/")
    if len(parts) != 2:
        raise click.ClickException("Repository must be in owner/name form.")
    return _destination_from_parts(parts[0], parts[1])


def validate_github_https_url(url: str) -> GitDestination:
    """Return a destination only for a plain, canonical GitHub HTTPS URL."""

    candidate = _require_safe_text(url, "Git remote URL")
    if "%" in candidate:
        raise click.ClickException("Git remote URL must not use percent-encoded path components.")
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError as exc:
        raise click.ClickException("Git remote URL is malformed.") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise click.ClickException("Git transport only supports credential-free github.com HTTPS URLs.")
    if parsed.netloc != "github.com":
        raise click.ClickException("Git transport only supports canonical github.com HTTPS URLs.")
    request_path = parsed.path.lstrip("/")
    if not request_path or parsed.path != "/" + request_path:
        raise click.ClickException("Git remote URL must contain a canonical owner/name path.")
    normalized = request_path[:-4] if request_path.endswith(".git") else request_path
    parts = normalized.split("/")
    if len(parts) != 2:
        raise click.ClickException("Git remote URL must contain a GitHub owner/name path.")
    destination = _destination_from_parts(parts[0], parts[1], suffix=".git" if request_path.endswith(".git") else "")
    return GitDestination(
        url=f"https://github.com/{request_path}",
        credential_path=destination.credential_path,
        request_path=request_path,
    )


def _run_git_read(args: list[str], *, cwd: Optional[str] = None) -> _GitResult:
    try:
        result = subprocess.run(
            ["git", *args],
            check=False,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=_without_unsafe_environment(),
        )
    except OSError as exc:
        raise click.ClickException("Git is unavailable for this transport operation.") from exc
    return _GitResult(result.returncode, result.stdout or "", result.stderr or "")


def _git_config_values(key: str, *, cwd: Optional[str] = None) -> list[str]:
    result = _run_git_read(["config", "--get-all", key], cwd=cwd)
    if result.returncode == 1:
        return []
    if result.returncode != 0:
        raise click.ClickException("Unable to inspect the current Git configuration.")
    return [line for line in result.stdout.splitlines() if line]


def _current_branch(*, cwd: Optional[str] = None) -> Optional[str]:
    result = _run_git_read(["branch", "--show-current"], cwd=cwd)
    if result.returncode != 0:
        raise click.ClickException("Current directory is not a usable Git checkout.")
    branch = (result.stdout or "").strip()
    return validate_branch(branch) if branch else None


@dataclass(frozen=True)
class _Upstream:
    remote: str
    branch: str
    current_branch: str


def current_upstream(*, cwd: Optional[str] = None) -> _Upstream:
    branch = _current_branch(cwd=cwd)
    if not branch:
        raise click.ClickException(
            "Cannot determine the current branch or its upstream. Pass REMOTE and a branch/refspec explicitly."
        )
    remotes = _git_config_values(f"branch.{branch}.remote", cwd=cwd)
    merges = _git_config_values(f"branch.{branch}.merge", cwd=cwd)
    if len(remotes) != 1 or len(merges) != 1:
        raise click.ClickException(
            f"Branch '{branch}' has no usable upstream. Pass REMOTE and a branch/refspec explicitly."
        )
    remote = validate_remote_name(remotes[0])
    merge = _require_safe_text(merges[0], "Configured upstream branch")
    prefix = "refs/heads/"
    if not merge.startswith(prefix):
        raise click.ClickException("Configured upstream branch must be under refs/heads/.")
    return _Upstream(remote=remote, branch=validate_branch(merge[len(prefix) :]), current_branch=branch)


def _remote_urls(remote: str, direction: str, *, cwd: Optional[str] = None) -> list[str]:
    remote = validate_remote_name(remote)
    if direction not in {"fetch", "push"}:
        raise ValueError(f"unsupported transport direction: {direction}")
    args = ["remote", "get-url", "--all"]
    if direction == "push":
        args.append("--push")
    args.append(remote)
    result = _run_git_read(args, cwd=cwd)
    if result.returncode != 0:
        raise click.ClickException(f"Git remote '{remote}' is not configured.")
    urls = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    unique = list(dict.fromkeys(urls))
    if not unique:
        raise click.ClickException(f"Git remote '{remote}' has no {direction} URL.")
    return unique


def destination_for_remote(remote: str, direction: str, *, cwd: Optional[str] = None) -> GitDestination:
    """Resolve Git's effective URL, after ``insteadOf``/``pushInsteadOf`` rules."""

    urls = _remote_urls(remote, direction, cwd=cwd)
    if len(urls) != 1:
        noun = "push" if direction == "push" else "fetch"
        raise click.ClickException(
            f"Refusing remote '{remote}' with multiple {noun} URLs; configure one HTTPS GitHub destination."
        )
    return validate_github_https_url(urls[0])


def _effective_clone_destination(destination: GitDestination, *, cwd: Optional[str] = None) -> GitDestination:
    """Validate the one ``insteadOf`` rewrite Git will apply to a clone URL.

    ``git clone`` receives a direct URL rather than a configured remote, so
    ``git remote get-url`` cannot expose its effective endpoint.  Git applies
    the longest matching ``insteadOf`` prefix once; mirror that documented
    selection before resolving a credential.  The original URL remains in the
    Git command so Git performs the same single rewrite.
    """

    result = _run_git_read(["config", "--get-regexp", r"^url\..*\.insteadOf$"], cwd=cwd)
    if result.returncode == 1:
        return destination
    if result.returncode != 0:
        raise click.ClickException("Unable to inspect configured Git URL rewrites.")

    matches: list[tuple[str, str]] = []
    suffix = ".insteadof"
    for line in result.stdout.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise click.ClickException("Unable to validate configured Git URL rewrites.")
        key, prefix = parts
        lowered = key.lower()
        if (
            not lowered.startswith("url.")
            or not lowered.endswith(suffix)
            or _contains_control(key)
            or _contains_control(prefix)
        ):
            raise click.ClickException("Unable to validate configured Git URL rewrites.")
        replacement = key[4 : len(key) - len(suffix)]
        if not replacement or not prefix:
            raise click.ClickException("Unable to validate configured Git URL rewrites.")
        if destination.url.startswith(prefix):
            matches.append((prefix, replacement))

    if not matches:
        return destination
    longest = max(len(prefix) for prefix, _replacement in matches)
    replacements = {replacement for prefix, replacement in matches if len(prefix) == longest}
    if len(replacements) != 1:
        raise click.ClickException("Refusing an ambiguous Git URL rewrite for clone.")
    prefix, _replacement = next((item for item in matches if len(item[0]) == longest))
    replacement = next(iter(replacements))
    return validate_github_https_url(replacement + destination.url[len(prefix) :])


def _reject_custom_remote_program(remote: str, direction: str, *, cwd: Optional[str] = None) -> None:
    key = f"remote.{validate_remote_name(remote)}.{ 'uploadpack' if direction == 'fetch' else 'receivepack' }"
    if _git_config_values(key, cwd=cwd):
        raise click.ClickException(
            f"Refusing authenticated {direction}: remote '{remote}' configures a custom Git program."
        )


def _resolve_token(
    token: Optional[str], destination: GitDestination, *, cwd: Optional[str] = None
) -> dict[str, Optional[str]]:
    info = resolve_token_with_source(token, credential_path=destination.credential_path, cwd=cwd)
    resolved = info["token"]
    if resolved and _contains_control(resolved):
        raise click.ClickException("GitHub token contains unsupported control characters.")
    return info


def _without_unsafe_environment(*, include_transport_token: bool = False) -> dict[str, str]:
    env = dict(os.environ)
    for key in list(env):
        if (
            key in _GIT_REPOSITORY_OVERRIDE_ENV
            or key in _AMBIENT_GITHUB_TOKEN_ENV
            or key == "GIT_CONFIG_COUNT"
            or key == "GIT_CONFIG_PARAMETERS"
            or key.startswith("GIT_CONFIG_KEY_")
            or key.startswith("GIT_CONFIG_VALUE_")
            or key.startswith("GIT_TRACE")
            or key in {"GIT_CURL_VERBOSE", "GIT_ASKPASS", "SSH_ASKPASS", "GIT_HTTP_EXTRAHEADER"}
            or (not include_transport_token and key.startswith("CHATGH_TRANSPORT_"))
        ):
            env.pop(key, None)
    return env


def _effective_config_names(*, cwd: Optional[str] = None) -> Iterable[str]:
    try:
        result = subprocess.run(
            ["git", "config", "--name-only", "--list"],
            check=False,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=_without_unsafe_environment(),
        )
    except OSError as exc:
        raise click.ClickException("Git is unavailable for this transport operation.") from exc
    if result.returncode != 0:
        raise click.ClickException("Unable to inspect the effective Git configuration.")
    return (line.strip() for line in (result.stdout or "").splitlines() if line.strip())


def _transport_config_pairs(destination: GitDestination, *, cwd: Optional[str] = None) -> list[tuple[str, str]]:
    header_keys = {"http.extraHeader"}
    helper_keys = {"credential.helper"}
    redirect_keys = {"http.followRedirects", f"http.{destination.url}.followRedirects"}
    path_keys = {"credential.useHttpPath", f"credential.{destination.url}.useHttpPath"}
    for key in _effective_config_names(cwd=cwd):
        lowered = key.lower()
        is_header = lowered.startswith("http.") and lowered.endswith(".extraheader")
        is_helper = lowered.startswith("credential.") and lowered.endswith(".helper")
        is_redirect = lowered == "http.followredirects" or (
            lowered.startswith("http.") and lowered.endswith(".followredirects")
        )
        is_path = lowered == "credential.usehttppath" or (
            lowered.startswith("credential.") and lowered.endswith(".usehttppath")
        )
        if (is_header or is_helper or is_redirect or is_path) and (
            not _CONFIG_KEY_RE.fullmatch(key) or _contains_control(key)
        ):
            raise click.ClickException(
                "Refusing inherited HTTP or credential configuration that cannot be reset safely."
            )
        if is_header:
            header_keys.add(key)
        if is_helper:
            helper_keys.add(key)
        if is_redirect:
            redirect_keys.add(key)
        if is_path:
            path_keys.add(key)

    pairs: list[tuple[str, str]] = []
    pairs.extend((key, "") for key in sorted(header_keys, key=str.lower))
    pairs.extend((key, "") for key in sorted(helper_keys, key=str.lower))
    pairs.extend((key, "false") for key in sorted(redirect_keys, key=str.lower))
    pairs.extend((key, "true") for key in sorted(path_keys, key=str.lower))
    pairs.extend(
        [
            # Hooks are disabled only for the authenticated Git child.  Local
            # merge/rebase/checkout work happens in a separate token-free child.
            ("core.hooksPath", os.devnull),
            ("submodule.recurse", "false"),
            ("protocol.file.allow", "never"),
        ]
    )
    return pairs


def build_transport_env(token: Optional[str], destination: GitDestination, *, cwd: Optional[str] = None) -> dict[str, str]:
    """Build the authenticated child's environment without serializing a token into config."""

    if token and _contains_control(token):
        raise click.ClickException("GitHub token contains unsupported control characters.")
    pairs = _transport_config_pairs(destination, cwd=cwd)
    env = _without_unsafe_environment()
    env.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never"})
    if token:
        helper_command = f"!{shlex.quote(sys.executable)} -m chatgh.github.transport credential-helper"
        # This exact URL helper is added after every inherited helper reset.
        pairs.append((f"credential.{destination.url}.helper", helper_command))
        env.update(
            {
                TOKEN_ENV: token,
                PROTOCOL_ENV: "https",
                HOST_ENV: "github.com",
                PATH_ENV: destination.request_path,
            }
        )
        # ``PYTHONPATH=src`` is common in source-tree development, but Git
        # runs its helper from the target repository.  Prepend the absolute
        # package root so the one-shot helper resolves the same module.
        package_root = str(Path(__file__).resolve().parents[2])
        inherited_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            package_root
            if not inherited_pythonpath
            else package_root + os.pathsep + inherited_pythonpath
        )
    env["GIT_CONFIG_COUNT"] = str(len(pairs))
    for index, (key, value) in enumerate(pairs):
        env[f"GIT_CONFIG_KEY_{index}"] = key
        env[f"GIT_CONFIG_VALUE_{index}"] = value
    return env


def _redact_git_text(value: str, token: Optional[str]) -> str:
    redacted = value or ""
    if not token:
        return redacted
    redacted = redacted.replace(token, "<redacted>")
    encoded = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")
    redacted = redacted.replace(encoded, "<redacted>")
    return re.sub(
        r"(?im)(authorization\s*:\s*(?:basic|bearer)\s+)[^\s\r\n]+",
        r"\1<redacted>",
        redacted,
    )


def _run_authenticated_git(
    args: list[str], destination: GitDestination, token: Optional[str], *, cwd: Optional[str] = None
) -> _GitResult:
    """Run exactly one network-facing Git child with a scoped helper."""

    env = build_transport_env(token, destination, cwd=cwd)
    try:
        result = subprocess.run(
            ["git", *args],
            check=False,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=env,
        )
    except OSError as exc:
        raise GitTransportError("Git is unavailable for this transport operation.") from exc
    stdout = _redact_git_text(result.stdout or "", token)
    stderr = _redact_git_text(result.stderr or "", token)
    if result.returncode != 0:
        detail = (stderr or stdout or "Git transport failed").strip()
        raise GitTransportError(detail, result.returncode)
    return _GitResult(result.returncode, stdout, stderr)


def _run_local_git(args: list[str], *, cwd: Optional[str] = None) -> _GitResult:
    """Run follow-up local work after the authenticated child has exited."""

    try:
        result = subprocess.run(
            ["git", *args],
            check=False,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=_without_unsafe_environment(),
        )
    except OSError as exc:
        raise GitTransportError("Git is unavailable for this transport operation.") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Git local operation failed").strip()
        raise GitTransportError(detail, result.returncode)
    return _GitResult(result.returncode, result.stdout or "", result.stderr or "")


def _fetch_target(remote: Optional[str], refspec: Optional[str], *, cwd: Optional[str]) -> tuple[str, Optional[str]]:
    if remote is None:
        upstream = current_upstream(cwd=cwd)
        resolved_remote = upstream.remote
    else:
        resolved_remote = validate_remote_name(remote)
    return resolved_remote, validate_refspec(refspec) if refspec else None


def fetch(
    remote: Optional[str] = None,
    refspec: Optional[str] = None,
    token: Optional[str] = None,
    *,
    cwd: Optional[str] = None,
) -> dict:
    """Fetch from a validated GitHub HTTPS remote with invocation-scoped auth."""

    resolved_remote, resolved_refspec = _fetch_target(remote, refspec, cwd=cwd)
    destination = destination_for_remote(resolved_remote, "fetch", cwd=cwd)
    _reject_custom_remote_program(resolved_remote, "fetch", cwd=cwd)
    token_info = _resolve_token(token, destination, cwd=cwd)
    command = ["fetch", "--recurse-submodules=no", resolved_remote]
    if resolved_refspec:
        command.append(resolved_refspec)
    result = _run_authenticated_git(command, destination, token_info["token"], cwd=cwd)
    return {
        "remote": resolved_remote,
        "refspec": resolved_refspec,
        "repo": destination.repo,
        "token_source": token_info["source"],
        "output": result.stdout.strip(),
    }


def _pull_target(remote: Optional[str], branch: Optional[str], *, cwd: Optional[str]) -> tuple[str, str]:
    upstream: Optional[_Upstream] = None
    if remote is None or branch is None:
        upstream = current_upstream(cwd=cwd)
    if remote is None:
        assert upstream is not None
        resolved_remote = upstream.remote
    else:
        resolved_remote = validate_remote_name(remote)
    if branch is None:
        assert upstream is not None
        if upstream.remote != resolved_remote:
            raise click.ClickException(
                f"Remote '{resolved_remote}' is not the current branch upstream. Pass BRANCH explicitly."
            )
        resolved_branch = upstream.branch
    else:
        resolved_branch = validate_branch(branch)
    return resolved_remote, resolved_branch


def pull(
    remote: Optional[str] = None,
    branch: Optional[str] = None,
    token: Optional[str] = None,
    ff_only: Optional[bool] = None,
    rebase: bool = False,
    *,
    cwd: Optional[str] = None,
) -> dict:
    """Fetch then fast-forward (or explicitly rebase) without secret-bearing local work."""

    if ff_only is None:
        ff_only = not rebase
    if rebase and ff_only:
        raise click.ClickException("Use either --ff-only or --rebase, not both.")
    resolved_remote, resolved_branch = _pull_target(remote, branch, cwd=cwd)
    destination = destination_for_remote(resolved_remote, "fetch", cwd=cwd)
    _reject_custom_remote_program(resolved_remote, "fetch", cwd=cwd)
    token_info = _resolve_token(token, destination, cwd=cwd)
    fetch_result = _run_authenticated_git(
        ["fetch", "--recurse-submodules=no", resolved_remote, resolved_branch],
        destination,
        token_info["token"],
        cwd=cwd,
    )
    if rebase:
        local_command = ["rebase", "FETCH_HEAD"]
    elif ff_only:
        local_command = ["merge", "--ff-only", "FETCH_HEAD"]
    else:
        local_command = ["merge", "FETCH_HEAD"]
    local_result = _run_local_git(local_command, cwd=cwd)
    return {
        "remote": resolved_remote,
        "branch": resolved_branch,
        "repo": destination.repo,
        "rebase": rebase,
        "ff_only": ff_only,
        "token_source": token_info["source"],
        "output": (fetch_result.stdout + local_result.stdout).strip(),
    }


def _push_target(
    remote: Optional[str], refspec: Optional[str], tags: bool, *, cwd: Optional[str]
) -> tuple[str, Optional[str]]:
    if tags and refspec:
        raise click.ClickException("--tags cannot be combined with REFSPEC.")
    upstream: Optional[_Upstream] = None
    if remote is None or (refspec is None and not tags):
        upstream = current_upstream(cwd=cwd)
    if remote is None:
        assert upstream is not None
        resolved_remote = upstream.remote
    else:
        resolved_remote = validate_remote_name(remote)
    if tags:
        return resolved_remote, None
    if refspec:
        return resolved_remote, validate_refspec(refspec)
    assert upstream is not None
    if upstream.remote != resolved_remote:
        raise click.ClickException(
            f"Remote '{resolved_remote}' is not the current branch upstream. Pass REFSPEC explicitly."
        )
    return resolved_remote, validate_refspec(f"{upstream.current_branch}:{upstream.branch}")


def push(
    remote: Optional[str] = None,
    refspec: Optional[str] = None,
    token: Optional[str] = None,
    set_upstream: bool = False,
    dry_run: bool = False,
    tags: bool = False,
    *,
    cwd: Optional[str] = None,
) -> dict:
    """Push only a validated refspec/tags set; force modes are intentionally absent."""

    if tags and set_upstream:
        raise click.ClickException("--set-upstream cannot be combined with --tags.")
    resolved_remote, resolved_refspec = _push_target(remote, refspec, tags, cwd=cwd)
    destination = destination_for_remote(resolved_remote, "push", cwd=cwd)
    _reject_custom_remote_program(resolved_remote, "push", cwd=cwd)
    token_info = _resolve_token(token, destination, cwd=cwd)
    command = ["push", "--recurse-submodules=no"]
    if set_upstream:
        command.append("--set-upstream")
    if dry_run:
        command.append("--dry-run")
    if tags:
        command.append("--tags")
    command.append(resolved_remote)
    if resolved_refspec:
        command.append(resolved_refspec)
    result = _run_authenticated_git(command, destination, token_info["token"], cwd=cwd)
    return {
        "remote": resolved_remote,
        "refspec": resolved_refspec,
        "repo": destination.repo,
        "set_upstream": set_upstream,
        "dry_run": dry_run,
        "tags": tags,
        "token_source": token_info["source"],
        "output": result.stdout.strip(),
    }


def clone_repository(
    repo: str,
    directory: str,
    token: Optional[str] = None,
    *,
    cwd: Optional[str] = None,
) -> dict:
    """Clone over HTTPS using the same scoped credential mechanism as fetch/push."""

    source_destination = destination_from_repo(repo)
    destination = _effective_clone_destination(source_destination, cwd=cwd)
    target = _require_safe_text(directory, "Clone directory")
    token_info = _resolve_token(token, destination, cwd=cwd)
    clone_result = _run_authenticated_git(
        ["clone", "--no-checkout", "--no-recurse-submodules", "--", source_destination.url, target],
        destination,
        token_info["token"],
        cwd=cwd,
    )
    # The checkout is intentionally token-free so repository filters/hooks do
    # not inherit credentials from the network-facing child.
    checkout_result = _run_local_git(["checkout"], cwd=str(Path(cwd or os.getcwd()) / target))
    return {
        "repo": destination.repo,
        "path": directory,
        "url": destination.url,
        "token_source": token_info["source"],
        "output": (clone_result.stdout + checkout_result.stdout).strip(),
    }


def _credential_fields(request: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in request.splitlines():
        if not line:
            break
        key, separator, value = line.partition("=")
        if not separator or not key or _contains_control(key) or _contains_control(value):
            return {}
        fields[key] = value
    return fields


def credential_helper_response(
    operation: str, request: str, *, env: Optional[Mapping[str, str]] = None
) -> str:
    """Implement Git's get/store/erase credential-helper protocol without persistence."""

    if operation != "get":
        return ""
    values = os.environ if env is None else env
    token = values.get(TOKEN_ENV, "")
    protocol = values.get(PROTOCOL_ENV, "")
    host = values.get(HOST_ENV, "")
    path = values.get(PATH_ENV, "").lstrip("/")
    if (
        not token
        or _contains_control(token)
        or protocol != "https"
        or host != "github.com"
        or not path
        or _contains_control(path)
    ):
        return ""
    fields = _credential_fields(request)
    request_path = fields.get("path", "").lstrip("/")
    if (
        fields.get("protocol") != protocol
        or fields.get("host") != host
        or request_path != path
        or _contains_control(request_path)
    ):
        return ""
    return f"username=x-access-token\npassword={token}\n\n"


def credential_helper_main(argv: Optional[list[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["credential-helper"]:
        args = args[1:]
    if len(args) != 1:
        return 0
    response = credential_helper_response(args[0], sys.stdin.read())
    if response:
        sys.stdout.write(response)
    return 0


def _pin_destination_for_remote(remote: str, *, cwd: Optional[str] = None) -> GitDestination:
    """Resolve a local token-pin target, including legacy GitHub SSH remotes.

    This helper is intentionally only for removing a pre-existing HTTPS config
    header. Network transports still reject SSH rather than converting it.
    """

    urls = _remote_urls(remote, "fetch", cwd=cwd)
    if len(urls) != 1:
        raise click.ClickException(f"Remote '{remote}' has multiple fetch URLs.")
    url = urls[0]
    try:
        return validate_github_https_url(url)
    except click.ClickException:
        pass
    candidate = _require_safe_text(url, "Git remote URL")
    path: Optional[str] = None
    if candidate.startswith("git@github.com:"):
        path = candidate[len("git@github.com:") :]
    elif candidate.startswith("ssh://git@github.com/"):
        path = candidate[len("ssh://git@github.com/") :]
    if path is None:
        raise click.ClickException("Current repository has no recognizable GitHub remote for a token pin.")
    normalized = path.removesuffix(".git")
    parts = normalized.split("/")
    if len(parts) != 2:
        raise click.ClickException("Current repository has no recognizable GitHub remote for a token pin.")
    return _destination_from_parts(parts[0], parts[1])


def _selected_destination(*, cwd: Optional[str] = None) -> GitDestination:
    try:
        upstream = current_upstream(cwd=cwd)
    except click.ClickException as exc:
        # A repository with no upstream can still remove the old origin-style
        # pin created by earlier ChatGH releases.  Do not silently bypass an
        # invalid configured upstream, though.
        if "no usable upstream" not in str(exc) and "Cannot determine" not in str(exc):
            raise
        remotes = _run_git_read(["remote"], cwd=cwd)
        names = [line.strip() for line in remotes.stdout.splitlines() if line.strip()]
        if "origin" in names:
            return _pin_destination_for_remote("origin", cwd=cwd)
        if len(names) == 1:
            return _pin_destination_for_remote(names[0], cwd=cwd)
        raise click.ClickException(
            "Current checkout has no selected GitHub remote. Configure an upstream or an origin remote first."
        )
    else:
        return _pin_destination_for_remote(upstream.remote, cwd=cwd)
    raise click.ClickException("Current repository has no recognizable GitHub HTTPS remote.")


def _config_path(*, cwd: Optional[str] = None) -> Path:
    result = _run_git_read(["rev-parse", "--git-path", "config"], cwd=cwd)
    if result.returncode != 0 or not result.stdout.strip():
        raise click.ClickException("Current directory is not a Git repository with local config.")
    path = Path(result.stdout.strip())
    if not path.is_absolute():
        path = Path(cwd or os.getcwd()) / path
    if path.is_symlink():
        raise click.ClickException("Refusing to edit a symlinked local Git config.")
    return path


def _unquote_git_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
        value = value.replace(r"\\", "\\").replace(r'\"', '"')
    return value


def _token_bearing_header(value: str) -> bool:
    prefix = "Authorization: Basic "
    if not value.startswith(prefix):
        return False
    try:
        decoded = base64.b64decode(value[len(prefix) :].strip(), validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    username, separator, token = decoded.partition(":")
    return username == "x-access-token" and separator == ":" and bool(token) and not _contains_control(token)


def _parse_local_header_removals(
    content: str, selected: GitDestination, all_tokens: bool
) -> tuple[list[int], list[str]]:
    lines = content.splitlines(keepends=True)
    current_url: Optional[str] = None
    removals: list[int] = []
    keys: list[str] = []
    for index, line in enumerate(lines):
        section = _SECTION_RE.match(line.rstrip("\r\n"))
        if section:
            current_url = _unquote_git_value(section.group("url"))
            continue
        if line.lstrip().startswith("["):
            current_url = None
            continue
        if not current_url:
            continue
        header = _EXTRAHEADER_RE.match(line)
        if not header:
            continue
        try:
            candidate = validate_github_https_url(current_url)
        except click.ClickException:
            continue
        if not all_tokens and candidate.credential_path["path"] != selected.credential_path["path"]:
            continue
        if not _token_bearing_header(_unquote_git_value(header.group("value"))):
            continue
        removals.append(index)
        key = f"http.{current_url}.extraHeader"
        if key not in keys:
            keys.append(key)
    return removals, keys


def _replace_config_file(path: Path, content: str) -> None:
    lock_path = path.with_name(path.name + ".lock")
    created_lock = False
    try:
        mode = path.stat().st_mode
        descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IMODE(mode))
        created_lock = True
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(lock_path, mode)
        os.replace(lock_path, path)
    except OSError as exc:
        try:
            if created_lock:
                lock_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise click.ClickException("Unable to update this repository's local Git config safely.") from exc


def unset_token(*, all_tokens: bool = False, cwd: Optional[str] = None) -> dict:
    """Remove only token-bearing GitHub HTTPS headers owned by local config."""

    selected = _selected_destination(cwd=cwd)
    path = _config_path(cwd=cwd)
    try:
        content = path.read_text(encoding="utf-8") if path.exists() else ""
    except (OSError, UnicodeError) as exc:
        raise click.ClickException("Unable to read this repository's local Git config.") from exc
    removals, keys = _parse_local_header_removals(content, selected, all_tokens)
    if removals:
        lines = content.splitlines(keepends=True)
        updated = "".join(line for index, line in enumerate(lines) if index not in set(removals))
        _replace_config_file(path, updated)
    token_info = resolve_token_with_source(None, credential_path=selected.credential_path, cwd=cwd)
    return {
        "repo": selected.repo,
        "removed_keys": keys,
        "removed_count": len(removals),
        "default_resolves": bool(token_info["token"]),
    }


if __name__ == "__main__":  # pragma: no cover - exercised by Git, not Click.
    raise SystemExit(credential_helper_main())

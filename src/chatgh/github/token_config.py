"""Repository token setting and explicit manifest-driven updates."""
from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click

from chatgh.github import api


@dataclass(frozen=True)
class RepositoryTarget:
    path: Path
    repo: str
    credential: api.CredentialQuery
    config_path: Path

    @property
    def key(self) -> str:
        return api._extraheader_config_key(self.credential)


def repository_target(path: Optional[str] = None) -> RepositoryTarget:
    root = Path(path or os.getcwd()).expanduser().resolve()
    if not root.is_dir():
        raise click.ClickException("Repository path does not exist or is not a directory.")
    repo, credential = api.resolve_repo_from_git_remote(cwd=str(root))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", repo):
        raise click.ClickException("Repository remote must name a valid GitHub owner/repository.")
    result = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-path", "config"],
        cwd=root, env=api._local_git_environment(), capture_output=True, text=True, check=False,
    )
    if result.returncode or not result.stdout.strip():
        raise click.ClickException("Repository has no local Git configuration.")
    config = Path(result.stdout.strip())
    if not config.is_absolute():
        config = root / config
    if config.is_symlink():
        raise click.ClickException("Refusing a symlinked repository Git config.")
    if credential["protocol"] != "https" or credential["host"] != "github.com" or credential["path"] != repo:
        raise click.ClickException("Repository remote must identify a supported GitHub HTTPS configuration target.")
    info = config.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise click.ClickException("Repository Git config must be a regular, unshared file.")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise click.ClickException("Repository Git config must be owned by the current user.")
    return RepositoryTarget(root, repo, credential, config)


def write_token(credential: api.CredentialQuery, token: str, cwd: Optional[str] = None) -> None:
    """Update one Git item losslessly, with no secret-bearing process arguments."""
    if not isinstance(token, str) or not token or re.search(r"[\x00-\x1f\x7f]", token):
        raise click.ClickException("GitHub token must be non-empty and contain no control characters.")
    target = repository_target(cwd)
    url = api.github_https_url(credential)
    if credential.get("host") != "github.com" or credential.get("protocol") != "https":
        raise click.ClickException("GitHub HTTPS configuration requires a supported GitHub target.")
    if not re.fullmatch(r"https://github\.com/[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*\.git", url):
        raise click.ClickException("GitHub configuration target is invalid.")
    lock = target.config_path.with_name(target.config_path.name + ".lock")
    identity = None
    try:
        # Acquire the native Git lock atomically BEFORE reading the original.
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        info = os.fstat(fd)
        identity = (info.st_dev, info.st_ino)
        with os.fdopen(fd, "wb") as handle:
            original = target.config_path.read_bytes()
            handle.write(original)
            handle.flush()
            os.fsync(handle.fileno())
        # Let Git preserve its own syntax and case semantics in our private
        # lock copy. Only a random, non-secret value goes through argv.
        import uuid
        marker = "chatgh-config-value-" + uuid.uuid4().hex
        if marker.encode("ascii") in original:
            raise ValueError("marker collision")
        result = subprocess.run(
            ["git", "config", "--no-includes", "--file", str(lock),
             "--replace-all", api._extraheader_config_key(credential), marker],
            cwd=target.path, env=api._local_git_environment(),
            capture_output=True, check=False,
        )
        if result.returncode:
            raise ValueError("native Git update failed")
        info = lock.lstat()
        identity = (info.st_dev, info.st_ino)
        encoded_marker = marker.encode("ascii")
        content = lock.read_bytes()
        if content.count(encoded_marker) != 1:
            raise ValueError("unexpected native Git output")
        updated = content.replace(encoded_marker, api.github_auth_extraheader(token).encode("ascii"))
        fd = os.open(lock, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "r+b") as handle:
            info = os.fstat(handle.fileno())
            if (info.st_dev, info.st_ino) != identity or not stat.S_ISREG(info.st_mode):
                raise ValueError("lock ownership changed")
            if os.name == "posix":
                os.fchmod(handle.fileno(), 0o600)
            handle.seek(0)
            handle.write(updated)
            handle.truncate()
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(lock, target.config_path)
        identity = None
    except Exception:
        raise click.ClickException("Unable to update the repository Git token configuration safely.") from None
    finally:
        # Never remove a foreign lock, including one created in an acquisition
        # race. Git manages its temporary config.lock.lock itself.
        if identity is not None:
            try:
                info = lock.lstat()
                if (info.st_dev, info.st_ino) == identity:
                    lock.unlink()
            except OSError:
                pass


def load_repository_targets(filename: str) -> tuple[list[RepositoryTarget], int]:
    manifest = Path(filename).expanduser().resolve()
    try:
        if manifest.stat().st_size > 256 * 1024:
            raise click.ClickException("Repository manifest exceeds the 256 KiB limit.")
        text = manifest.read_text(encoding="utf-8")
        if manifest.suffix.lower() == ".json":
            data = json.loads(text)
        elif manifest.suffix.lower() in {".yaml", ".yml"}:
            import yaml
            data = yaml.safe_load(text)
        else:
            raise click.ClickException("Repository manifest must be JSON or YAML.")
    except click.ClickException:
        raise
    except Exception:
        raise click.ClickException("Unable to parse repository manifest; values are not included in errors.") from None
    if not isinstance(data, dict) or set(data) - {"version", "repositories"}:
        raise click.ClickException("Repository manifest must contain only version and repositories; do not store tokens.")
    if type(data.get("version", 1)) is not int or data.get("version", 1) != 1:
        raise click.ClickException("Unsupported repository manifest version.")
    entries = data.get("repositories")
    if not isinstance(entries, list) or not entries or len(entries) > 1000:
        raise click.ClickException("Repository manifest requires 1–1000 repository entries.")
    targets = []
    seen = set()
    for index, entry in enumerate(entries, start=1):
        expected_repo = None
        if isinstance(entry, str):
            raw_path = entry
        elif isinstance(entry, dict) and not set(entry) - {"path", "repo"}:
            raw_path = entry.get("path")
            expected_repo = entry.get("repo")
        else:
            raise click.ClickException(f"Repository entry {index} has unsupported fields or type.")
        if not isinstance(raw_path, str) or not raw_path.strip() or re.search(r"[\x00-\x1f\x7f]", raw_path):
            raise click.ClickException(f"Repository entry {index} needs a valid path.")
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = manifest.parent / path
        target = repository_target(str(path))
        if expected_repo is not None and expected_repo != target.repo:
            raise click.ClickException(f"Repository entry {index} does not match its declared repository.")
        identity = (target.config_path.resolve(), target.key)
        if identity not in seen:
            targets.append(target)
            seen.add(identity)
    return targets, len(entries)


def set_repository_tokens(
    token: Optional[str], save_env: bool, *, from_config: bool = False,
    repo_file: Optional[str] = None, dry_run: bool = False,
) -> dict:
    if from_config and token is not None:
        raise click.ClickException("Cannot combine --from-config with --token.")
    if repo_file and save_env:
        raise click.ClickException("Cannot combine --file with --save-env.")
    if repo_file and not from_config and token is None:
        raise click.ClickException("Batch updates require --from-config or an explicit --token.")
    # Resolve and validate the complete inventory BEFORE loading a credential.
    targets, requested = load_repository_targets(repo_file) if repo_file else ([repository_target()], 1)
    if from_config:
        resolved = api.get_github_config_token()
    else:
        first = targets[0]
        resolved = api.resolve_token(token, credential_path=first.credential, cwd=str(first.path))
    if not resolved:
        raise click.ClickException("Missing GitHub token in the selected source.")
    if re.search(r"[\x00-\x1f\x7f]", resolved):
        raise click.ClickException("GitHub token contains unsupported control characters.")
    results = []
    for target in targets:
        row = {"path": str(target.path), "repo": target.repo, "key": target.key, "configured": False}
        try:
            if not dry_run:
                write_token(target.credential, resolved, str(target.path))
                if api.read_github_token_from_git(target.credential, cwd=str(target.path)) != resolved:
                    raise click.ClickException("Repository token update did not pass readback.")
            row["configured"] = not dry_run
            row["status"] = "planned" if dry_run else "configured"
        except click.ClickException:
            row["status"] = "failed"
            row["error"] = "Unable to write repository token configuration."
        results.append(row)
    failed = sum(row["status"] == "failed" for row in results)
    if not repo_file:
        if failed:
            raise click.ClickException(results[0]["error"])
        if save_env and not dry_run:
            api.save_github_token_to_env(resolved)
        return {"repo": targets[0].repo, "saved_env": save_env and not dry_run, "configured": not dry_run, "dry_run": dry_run}
    return {
        "requested": requested, "total": len(targets), "duplicates_skipped": requested - len(targets),
        "configured": sum(row["configured"] for row in results), "failed": failed,
        "dry_run": dry_run, "repositories": results,
    }

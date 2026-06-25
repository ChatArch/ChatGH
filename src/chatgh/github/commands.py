from __future__ import annotations

import subprocess
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import click

from chatgh.github.api import (
    CredentialQuery,
    configure_github_https_token,
    credential_path_from_repo,
    get_client,
    resolve_repo,
    resolve_repo_from_git_remote,
    resolve_token,
    resolve_token_with_source,
    save_github_token_to_env,
    split_repo,
)
from chatgh.github.render import (
    collect_merge_blockers,
    derive_repo_capabilities,
    has_incomplete_pr_checks,
    tail_text,
)
from chatgh.github.requests import (
    download_run_artifact_zip,
    get_job_logs,
    get_pr_checks,
    get_pr_list,
    get_pr_diff_text,
    get_pr_view,
    get_repo_list,
    get_repo_view_payload,
    get_repo_names,
    get_repo_permissions,
    get_repo_protection,
    get_run_list,
    get_run_view,
    patch_pr_edit,
    patch_repo_edit,
    post_pr_comment,
    post_pr_create,
    post_pr_merge,
    post_pr_ready,
    post_pr_review,
    post_pr_update_branch,
    post_run_action,
    post_repo_create,
    post_repo_fork,
)


def resolve_repo_and_credential_path(repo: Optional[str]) -> tuple[str, CredentialQuery]:
    if repo:
        normalized = resolve_repo(repo)
        return normalized, credential_path_from_repo(normalized)
    return resolve_repo_from_git_remote()


def list_repos(
    owner: str,
    limit: int,
    sort: str,
    direction: str,
    token: Optional[str],
) -> list[dict]:
    credential_path = credential_path_from_repo(f"{owner}/_")
    client = get_client(token, require_token=True, credential_path=credential_path)
    return get_repo_list(client, owner, limit, sort, direction)


def inspect_repo_protection(repo: str, token: Optional[str]) -> dict:
    resolved_repo = resolve_repo(repo)
    credential_path = credential_path_from_repo(resolved_repo)
    resolved_token = resolve_token(token, credential_path=credential_path)
    return get_repo_protection(resolved_repo, resolved_token)


def list_repo_protections(owner: str, limit: int, token: Optional[str], jobs: int = 8) -> list[dict]:
    credential_path = credential_path_from_repo(f"{owner}/_")
    client = get_client(token, require_token=True, credential_path=credential_path)
    repo_names = get_repo_names(client, owner, limit)
    resolved_token = resolve_token(token, credential_path=credential_path)
    if not repo_names:
        return []
    worker_count = max(1, min(jobs, len(repo_names)))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        return list(executor.map(lambda repo: get_repo_protection(repo, resolved_token), repo_names))


def create_repo(
    owner: str,
    name: str,
    private: bool,
    description: Optional[str],
    if_exists: str,
    token: Optional[str],
) -> dict:
    credential_path = credential_path_from_repo(f"{owner}/{name}")
    client = get_client(token, require_token=True, credential_path=credential_path)
    try:
        return post_repo_create(client, owner, name, private, description, if_exists)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def fork_repo(
    source: str,
    owner: str,
    name: Optional[str],
    default_branch_only: bool,
    if_exists: str,
    token: Optional[str],
) -> dict:
    source_repo = resolve_repo(source)
    _, source_name = split_repo(source_repo)
    target_name = name or source_name
    credential_path = credential_path_from_repo(f"{owner}/{target_name}")
    resolved_token = resolve_token(token, credential_path=credential_path)
    if not resolved_token:
        raise click.ClickException(
            "Missing token. Pass --token or run `chatgh set-token` inside the current repository to configure a repo-scoped GitHub credential."
        )
    try:
        return post_repo_fork(
            source_repo,
            owner=owner,
            name=target_name,
            default_branch_only=default_branch_only,
            if_exists=if_exists,
            token=resolved_token,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc



def view_repo(repo: Optional[str], token: Optional[str]) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    resolved_token = resolve_token(token, credential_path=credential_path)
    return get_repo_view_payload(resolved_repo, resolved_token)


def edit_repo(
    repo: Optional[str],
    description: Optional[str],
    homepage: Optional[str],
    default_branch: Optional[str],
    visibility: Optional[str],
    accept_visibility_change_consequences: bool,
    token: Optional[str],
) -> dict:
    if visibility is not None and not accept_visibility_change_consequences:
        raise click.ClickException(
            "Changing repository visibility can expose or hide repository data. "
            "Pass --accept-visibility-change-consequences to confirm this remote mutation."
        )
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    resolved_token = resolve_token(token, credential_path=credential_path)
    if not resolved_token:
        raise click.ClickException("Missing token. Pass --token or configure a repo-scoped GitHub credential.")
    return patch_repo_edit(
        resolved_repo,
        resolved_token,
        description=description,
        homepage=homepage,
        default_branch=default_branch,
        visibility=visibility,
    )


def clone_repo(repo: str, directory: Optional[str], ssh: bool, token: Optional[str]) -> dict:
    resolved_repo = resolve_repo(repo)
    _owner, name = split_repo(resolved_repo)
    target_dir = Path(directory or name)
    if target_dir.exists() and any(target_dir.iterdir()):
        raise click.ClickException(f"Target directory already exists and is not empty: {target_dir}")
    url = f"git@github.com:{resolved_repo}.git" if ssh else f"https://github.com/{resolved_repo}.git"
    command = ["git", "clone", url, str(target_dir)]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise click.ClickException((result.stderr or result.stdout or "git clone failed").strip())
    return {"repo": resolved_repo, "path": str(target_dir), "url": url}


def sync_repo(repo: Optional[str], branch: Optional[str], remote: str, ff_only: bool, token: Optional[str]) -> dict:
    current_repo, _credential_path = resolve_repo_from_git_remote()
    if repo is not None:
        requested_repo = resolve_repo(repo)
        if requested_repo.lower() != current_repo.lower():
            raise click.ClickException(
                f"Refusing to sync {requested_repo}: current checkout is {current_repo}. "
                "Run this command inside the matching checkout or omit the repo argument."
            )
        resolved_repo = requested_repo
    else:
        resolved_repo = current_repo
    fetch = subprocess.run(["git", "fetch", remote], check=False, capture_output=True, text=True)
    if fetch.returncode != 0:
        raise click.ClickException((fetch.stderr or fetch.stdout or "git fetch failed").strip())
    if branch is None:
        branch_result = subprocess.run(["git", "branch", "--show-current"], check=False, capture_output=True, text=True)
        branch = (branch_result.stdout or "").strip()
    if not branch:
        raise click.ClickException("Cannot determine current branch. Pass --branch.")
    pull_command = ["git", "pull"]
    if ff_only:
        pull_command.append("--ff-only")
    pull_command.extend([remote, branch])
    pull = subprocess.run(pull_command, check=False, capture_output=True, text=True)
    if pull.returncode != 0:
        raise click.ClickException((pull.stderr or pull.stdout or "git pull failed").strip())
    return {"repo": resolved_repo, "remote": remote, "branch": branch, "output": (pull.stdout or "").strip()}

def create_pr(
    repo: Optional[str],
    base: str,
    head: str,
    title: str,
    body: str,
    token: Optional[str],
) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    client = get_client(token, require_token=True, credential_path=credential_path)
    return post_pr_create(client, resolved_repo, base, head, title, body)


def list_prs(
    repo: Optional[str],
    state: str,
    limit: int,
    token: Optional[str],
) -> list[dict]:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    client = get_client(token, credential_path=credential_path)
    return get_pr_list(client, resolved_repo, state, limit)


def view_pr(repo: Optional[str], number: int, token: Optional[str]) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    client = get_client(token, credential_path=credential_path)
    return get_pr_view(client, resolved_repo, number)


def check_pr(
    repo: Optional[str],
    number: int,
    check_limit: int,
    workflow_limit: int,
    wait_for_completion: bool,
    interval: float,
    timeout: Optional[float],
    token: Optional[str],
) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    client = get_client(token, credential_path=credential_path)
    started_at = time.monotonic()
    while True:
        payload = get_pr_checks(
            client,
            resolved_repo,
            number,
            check_limit=check_limit,
            workflow_limit=workflow_limit,
        )
        if not wait_for_completion or not has_incomplete_pr_checks(payload):
            return payload
        if timeout is not None and (time.monotonic() - started_at) >= timeout:
            raise click.ClickException(
                f"Timed out after {timeout:g}s waiting for PR #{number} checks to finish."
            )
        click.echo(
            f"Waiting for PR #{number} checks to finish; polling again in {interval:g}s...",
            err=True,
        )
        time.sleep(interval)



def status_prs(repo: Optional[str], token: Optional[str]) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    client = get_client(token, credential_path=credential_path)
    return {"repo": resolved_repo, "open": get_pr_list(client, resolved_repo, "open", 20)}


def diff_pr(repo: Optional[str], number: int, token: Optional[str]) -> str:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    resolved_token = resolve_token(token, credential_path=credential_path)
    return get_pr_diff_text(resolved_repo, number, resolved_token)


def close_pr(repo: Optional[str], number: int, comment: Optional[str], delete_branch: bool, token: Optional[str]) -> dict:
    if comment:
        comment_pr(repo, number, comment, token)
    payload = edit_pr(repo, number, None, None, "closed", None, token)
    payload["delete_branch_requested"] = delete_branch
    return payload


def reopen_pr(repo: Optional[str], number: int, token: Optional[str]) -> dict:
    return edit_pr(repo, number, None, None, "open", None, token)


def review_pr(repo: Optional[str], number: int, event: str, body: str, token: Optional[str]) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    client = get_client(token, require_token=True, credential_path=credential_path)
    return post_pr_review(client, resolved_repo, number, event, body)


def ready_pr(repo: Optional[str], number: int, token: Optional[str]) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    resolved_token = resolve_token(token, credential_path=credential_path)
    if not resolved_token:
        raise click.ClickException("Missing token. Pass --token or configure a repo-scoped GitHub credential.")
    return post_pr_ready(resolved_repo, number, resolved_token)


def update_pr_branch(repo: Optional[str], number: int, expected_head_sha: Optional[str], token: Optional[str]) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    resolved_token = resolve_token(token, credential_path=credential_path)
    if not resolved_token:
        raise click.ClickException("Missing token. Pass --token or configure a repo-scoped GitHub credential.")
    return post_pr_update_branch(resolved_repo, number, resolved_token, expected_head_sha)

def comment_pr(repo: Optional[str], number: int, body: str, token: Optional[str]) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    client = get_client(token, require_token=True, credential_path=credential_path)
    return post_pr_comment(client, resolved_repo, number, body)


def merge_pr(
    repo: Optional[str],
    number: int,
    method: str,
    title: Optional[str],
    message: Optional[str],
    check_before_merge: bool,
    token: Optional[str],
) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    client = get_client(token, require_token=True, credential_path=credential_path)
    if check_before_merge:
        payload = get_pr_checks(
            client,
            resolved_repo,
            number,
            check_limit=20,
            workflow_limit=10,
        )
        blockers = collect_merge_blockers(payload)
        if blockers:
            details = "\n".join(f"- {item}" for item in blockers)
            raise click.ClickException(
                "Refusing to merge because CI checks are not green:\n"
                f"{details}\n"
                f"Run `chatgh pr checks {number}` for details, "
                "or rerun without `--check` if you intentionally want to merge anyway."
            )
    result = post_pr_merge(client, resolved_repo, number, method, title, message)
    if not result["merged"]:
        raise click.ClickException(f"Merge failed: {result['message']}")
    return result


def edit_pr(
    repo: Optional[str],
    number: int,
    title: Optional[str],
    body: Optional[str],
    state: Optional[str],
    base: Optional[str],
    token: Optional[str],
) -> dict:
    if title is None and body is None and state is None and base is None:
        raise click.ClickException("No updates provided. Use --title/--body/--state/--base.")
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    client = get_client(token, require_token=True, credential_path=credential_path)
    return patch_pr_edit(
        client,
        resolved_repo,
        number,
        title=title,
        body=body,
        state=state,
        base=base,
    )


def view_run(
    repo: Optional[str],
    run_id: int,
    job_limit: int,
    token: Optional[str],
) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    resolved_token = resolve_token(token, credential_path=credential_path)
    return get_run_view(resolved_repo, run_id, resolved_token, job_limit)


def view_job_logs(
    repo: Optional[str],
    job_id: int,
    tail: int,
    output: Optional[str],
    token: Optional[str],
) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    resolved_token = resolve_token(token, credential_path=credential_path)
    payload = get_job_logs(resolved_repo, job_id, resolved_token)
    rendered_log = tail_text(payload["log"], tail)
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(payload["log"])
    return {
        "job": payload["job"],
        "tail": tail,
        "output_path": output,
        "log": payload["log"],
        "rendered_log": rendered_log,
    }



def list_runs(
    repo: Optional[str],
    branch: Optional[str],
    status: Optional[str],
    event: Optional[str],
    limit: int,
    token: Optional[str],
) -> list[dict]:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    resolved_token = resolve_token(token, credential_path=credential_path)
    return get_run_list(resolved_repo, resolved_token, branch=branch, status=status, event=event, limit=limit)


def watch_run(repo: Optional[str], run_id: int, interval: float, timeout: Optional[float], token: Optional[str]) -> dict:
    started_at = time.monotonic()
    while True:
        payload = view_run(repo, run_id, 100, token)
        if payload.get("status") == "completed":
            return payload
        if timeout is not None and (time.monotonic() - started_at) >= timeout:
            raise click.ClickException(f"Timed out after {timeout:g}s waiting for run {run_id} to finish.")
        click.echo(f"Waiting for run {run_id}; status={payload.get('status')}; polling again in {interval:g}s...", err=True)
        time.sleep(interval)


def rerun_run(repo: Optional[str], run_id: int, token: Optional[str]) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    resolved_token = resolve_token(token, credential_path=credential_path)
    if not resolved_token:
        raise click.ClickException("Missing token. Pass --token or configure a repo-scoped GitHub credential.")
    return post_run_action(resolved_repo, run_id, resolved_token, "rerun")


def cancel_run(repo: Optional[str], run_id: int, token: Optional[str]) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    resolved_token = resolve_token(token, credential_path=credential_path)
    if not resolved_token:
        raise click.ClickException("Missing token. Pass --token or configure a repo-scoped GitHub credential.")
    return post_run_action(resolved_repo, run_id, resolved_token, "cancel")


def download_run_artifacts(repo: Optional[str], run_id: int, name: Optional[str], output_dir: str, token: Optional[str]) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    resolved_token = resolve_token(token, credential_path=credential_path)
    if not resolved_token:
        raise click.ClickException("Missing token. Pass --token or configure a repo-scoped GitHub credential.")
    return download_run_artifact_zip(resolved_repo, run_id, resolved_token, name=name, output_dir=output_dir)

def repo_perms(repo: Optional[str], full_json: bool, token: Optional[str]) -> dict:
    resolved_repo, credential_path = resolve_repo_and_credential_path(repo)
    token_info = resolve_token_with_source(token, credential_path=credential_path)
    resolved_token = token_info["token"]
    payload = get_repo_permissions(resolved_repo, resolved_token)
    permissions = payload.get("permissions") or {}
    result = {
        "repo": payload.get("full_name") or resolved_repo,
        "private": payload.get("private"),
        "visibility": payload.get("visibility"),
        "token_mask": mask_token(resolved_token),
        "token_source": token_info["source"],
        "permissions": permissions,
        "capabilities": derive_repo_capabilities(permissions),
    }
    if full_json:
        result["repository"] = payload
    return result


def mask_token(token: Optional[str]) -> str:
    if not token:
        return "<none>"
    if len(token) <= 12:
        return token[:2] + "..." + token[-2:]
    return token[:7] + "..." + token[-5:]


def set_token(token: Optional[str], save_env: bool) -> dict:
    repo, credential_path = resolve_repo_from_git_remote()
    resolved_token = resolve_token(
        token,
        credential_path=credential_path,
        exact_only=True,
    ) or resolve_token(token, credential_path=credential_path)
    if not resolved_token:
        raise click.ClickException(
            "Missing token. Provide --token or configure a GitHub credential for the current repository."
        )
    configure_github_https_token(credential_path, resolved_token)
    if save_env:
        save_github_token_to_env(resolved_token)
    return {"repo": repo, "saved_env": save_env}

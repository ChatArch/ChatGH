from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import click

from chatgh.github.api import github_api_get_json, github_api_get_text, github_api_headers, split_repo


def get_repo_list(
    client,
    owner: str,
    limit: int,
    sort: str,
    direction: str,
) -> list[dict]:
    owner_obj = _get_owner(client, owner)
    items: list[dict] = []
    for repo in owner_obj.get_repos():
        items.append(_build_repo_payload(repo))
    items.sort(
        key=lambda item: _repo_sort_key(item, sort),
        reverse=(direction == "desc"),
    )
    return items[:limit]


def get_repo_names(client, owner: str, limit: int) -> list[str]:
    owner_obj = _get_owner(client, owner)
    names = [repo.full_name for repo in owner_obj.get_repos()]
    names.sort(key=str.lower)
    return names[:limit]


def post_repo_create(
    client,
    owner: str,
    name: str,
    private: bool,
    description: Optional[str],
    if_exists: str,
) -> dict:
    full_name = f"{owner}/{name}"
    try:
        existing = client.get_repo(full_name)
    except Exception as exc:
        if getattr(exc, "status", None) != 404:
            raise
    else:
        if if_exists == "use":
            payload = _build_repo_payload(existing)
            payload["created"] = False
            return payload
        raise ValueError(f"Repository already exists: {full_name}")

    owner_obj = _get_owner(client, owner)
    repo = owner_obj.create_repo(
        name=name,
        private=private,
        description=description or "",
    )
    payload = _build_repo_payload(repo)
    payload["created"] = True
    return payload


def post_repo_fork(
    source: str,
    owner: str,
    name: str,
    default_branch_only: bool,
    if_exists: str,
    token: Optional[str],
) -> dict:
    import requests

    source_owner, source_name = split_repo(source)
    target_full_name = f"{owner}/{name}"
    existing = _get_repo_json_optional(target_full_name, token)
    if existing is not None:
        if if_exists != "use":
            raise ValueError(f"Repository already exists: {target_full_name}")
        source_full_name = _source_full_name_from_repo_json(existing)
        if not _repo_names_equal(source_full_name, source):
            actual = source_full_name or "a non-fork repository"
            raise ValueError(
                f"Repository already exists but is {actual}, not a fork of {source}: {target_full_name}"
            )
        payload = _build_repo_payload_from_json(existing)
        payload["created"] = False
        payload["source_full_name"] = source_full_name
        return payload

    request_payload = _build_fork_request_payload(owner, name, default_branch_only, token)
    url = f"https://api.github.com/repos/{source_owner}/{source_name}/forks"
    try:
        response = requests.post(
            url,
            headers=github_api_headers(token),
            json=request_payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise click.ClickException(f"GitHub API request failed for /forks: {exc}") from exc
    if not response.ok:
        detail = _response_error_detail(response)
        raise click.ClickException(
            f"GitHub API error ({response.status_code}) for /forks: {detail}. If this repository should use a dedicated token, run `chatgh set-token` inside the repo to add a matching git credential entry."
        )
    try:
        repo_payload = response.json()
    except ValueError as exc:
        raise click.ClickException("GitHub API returned non-JSON response for /forks") from exc
    payload = _build_repo_payload_from_json(repo_payload)
    payload["created"] = True
    payload["source_full_name"] = _source_full_name_from_repo_json(repo_payload) or source
    return payload


def _get_repo_json_optional(repo: str, token: Optional[str]) -> Optional[dict]:
    import requests

    owner, name = split_repo(repo)
    url = f"https://api.github.com/repos/{owner}/{name}"
    try:
        response = requests.get(url, headers=github_api_headers(token), timeout=30)
    except requests.RequestException as exc:
        raise click.ClickException(f"GitHub API request failed for {repo}: {exc}") from exc
    if response.status_code == 404:
        return None
    if not response.ok:
        detail = _response_error_detail(response)
        raise click.ClickException(f"GitHub API error ({response.status_code}) for {repo}: {detail}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise click.ClickException(f"GitHub API returned non-JSON response for {repo}") from exc
    return payload if isinstance(payload, dict) else None


def _build_fork_request_payload(
    owner: str,
    name: str,
    default_branch_only: bool,
    token: Optional[str],
) -> dict[str, object]:
    payload: dict[str, object] = {"name": name}
    if _github_owner_type(owner, token) == "Organization":
        payload["organization"] = owner
    else:
        authenticated_login = _authenticated_user_login(token)
        if not _repo_names_equal(authenticated_login, owner):
            raise click.ClickException(
                "Forking into a user account requires --owner to match the authenticated GitHub user. "
                "Use an organization owner or authenticate as the target user."
            )
    if default_branch_only:
        payload["default_branch_only"] = True
    return payload


def _github_owner_type(owner: str, token: Optional[str]) -> str:
    payload = _github_get_json_url(f"https://api.github.com/users/{owner}", token, f"users/{owner}")
    owner_type = str(payload.get("type") or "")
    return owner_type or "User"


def _authenticated_user_login(token: Optional[str]) -> Optional[str]:
    payload = _github_get_json_url("https://api.github.com/user", token, "user")
    login = payload.get("login")
    return str(login) if login else None


def _github_get_json_url(url: str, token: Optional[str], label: str) -> dict:
    import requests

    try:
        response = requests.get(url, headers=github_api_headers(token), timeout=30)
    except requests.RequestException as exc:
        raise click.ClickException(f"GitHub API request failed for {label}: {exc}") from exc
    if not response.ok:
        detail = _response_error_detail(response)
        raise click.ClickException(f"GitHub API error ({response.status_code}) for {label}: {detail}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise click.ClickException(f"GitHub API returned non-JSON response for {label}") from exc
    return payload if isinstance(payload, dict) else {}


def _response_error_detail(response) -> str:
    detail = (response.text or "").strip()
    try:
        payload = response.json()
        if isinstance(payload, dict) and payload.get("message"):
            detail = str(payload["message"])
    except ValueError:
        pass
    return detail or "unknown error"


def _source_full_name_from_repo_json(payload: dict) -> Optional[str]:
    for key in ("source", "parent"):
        candidate = payload.get(key)
        if isinstance(candidate, dict) and candidate.get("full_name"):
            return str(candidate["full_name"])
    return None


def _repo_names_equal(left: Optional[str], right: Optional[str]) -> bool:
    if not left or not right:
        return False
    return left.strip().lower() == right.strip().lower()


def _build_repo_payload_from_json(payload: dict) -> dict:
    open_prs = None
    open_issues_reported = payload.get("open_issues_count")
    open_issues = int(open_issues_reported or 0) if open_issues_reported is not None else None
    return {
        "name": payload.get("name"),
        "full_name": payload.get("full_name"),
        "private": payload.get("private"),
        "visibility": payload.get("visibility") or ("private" if payload.get("private") else "public"),
        "stars": int(payload.get("stargazers_count") or 0),
        "forks": int(payload.get("forks_count") or 0),
        "open_prs": open_prs,
        "open_issues": open_issues,
        "open_issues_reported": open_issues_reported,
        "archived": bool(payload.get("archived", False)),
        "fork": bool(payload.get("fork", False)),
        "created_at": payload.get("created_at"),
        "updated_at": payload.get("updated_at"),
        "pushed_at": payload.get("pushed_at"),
        "html_url": payload.get("html_url"),
        "clone_url": payload.get("clone_url"),
        "ssh_url": payload.get("ssh_url"),
        "default_branch": payload.get("default_branch"),
        "description": payload.get("description"),
    }


def get_pr_list(client, repo: str, state: str, limit: int) -> list[dict]:
    repo_obj = client.get_repo(repo)
    items: list[dict] = []
    for pr in repo_obj.get_pulls(state=state, sort="updated", direction="desc"):
        items.append(_build_pr_view_payload(pr))
        if len(items) >= limit:
            break
    return items


def get_repo_protection(repo: str, token: Optional[str]) -> dict:
    repo_payload = github_api_get_json(repo, "", token)
    default_branch = repo_payload.get("default_branch")
    errors: list[str] = []
    branch_protection = {"enabled": False}
    default_branch_protected: Optional[bool] = None

    if default_branch:
        branch_path = quote(str(default_branch), safe="")
        try:
            branch_payload = github_api_get_json(repo, f"/branches/{branch_path}", token)
            default_branch_protected = bool(branch_payload.get("protected"))
        except Exception as exc:
            errors.append(f"branch: {exc}")
            default_branch_protected = None

        if default_branch_protected:
            try:
                protection_payload = github_api_get_json(
                    repo, f"/branches/{branch_path}/protection", token
                )
                branch_protection = _build_branch_protection_payload(protection_payload)
            except Exception as exc:
                branch_protection = {"enabled": True, "error": str(exc)}
                errors.append(f"branch protection: {exc}")
    else:
        errors.append("default branch missing")

    rulesets: list[dict] = []
    try:
        ruleset_payload = github_api_get_json(repo, "/rulesets", token)
        if isinstance(ruleset_payload, list):
            rulesets = [_build_ruleset_summary(item) for item in ruleset_payload]
    except Exception as exc:
        errors.append(f"rulesets: {exc}")

    return {
        "repo": repo_payload.get("full_name") or repo,
        "private": repo_payload.get("private"),
        "visibility": repo_payload.get("visibility"),
        "default_branch": default_branch,
        "default_branch_protected": default_branch_protected,
        "branch_protection": branch_protection,
        "rulesets": rulesets,
        "ruleset_count": len(rulesets),
        "errors": errors,
    }


def _build_branch_protection_payload(payload: dict) -> dict:
    reviews = payload.get("required_pull_request_reviews") or None
    return {
        "enabled": True,
        "required_pull_request_reviews": reviews is not None,
        "required_approving_review_count": (
            reviews or {}
        ).get("required_approving_review_count"),
        "allow_force_pushes": (payload.get("allow_force_pushes") or {}).get("enabled"),
        "allow_deletions": (payload.get("allow_deletions") or {}).get("enabled"),
        "required_status_checks": payload.get("required_status_checks") is not None,
        "enforce_admins": (payload.get("enforce_admins") or {}).get("enabled"),
    }


def _build_ruleset_summary(payload: dict) -> dict:
    rules = payload.get("rules") or []
    return {
        "id": payload.get("id"),
        "name": payload.get("name"),
        "target": payload.get("target"),
        "enforcement": payload.get("enforcement"),
        "rule_count": len(rules),
        "rules": [rule.get("type") for rule in rules if isinstance(rule, dict)],
    }


def get_pr_view(client, repo: str, number: int) -> dict:
    repo_obj = client.get_repo(repo)
    pr = repo_obj.get_pull(number)
    return _build_pr_view_payload(pr)


def _get_owner(client, owner: str):
    try:
        return client.get_organization(owner)
    except Exception as exc:
        if getattr(exc, "status", None) not in {403, 404}:
            raise
    return client.get_user(owner)


def _build_repo_payload(repo) -> dict:
    open_prs = _safe_count(lambda: repo.get_pulls(state="open"))
    open_issues_reported = int(getattr(repo, "open_issues_count", 0) or 0)
    open_issues = max(open_issues_reported - open_prs, 0) if open_prs is not None else None
    return {
        "name": repo.name,
        "full_name": repo.full_name,
        "private": repo.private,
        "visibility": getattr(repo, "visibility", None) or ("private" if repo.private else "public"),
        "stars": int(getattr(repo, "stargazers_count", 0) or 0),
        "forks": int(getattr(repo, "forks_count", 0) or 0),
        "open_prs": open_prs,
        "open_issues": open_issues,
        "open_issues_reported": open_issues_reported,
        "archived": bool(getattr(repo, "archived", False)),
        "fork": bool(getattr(repo, "fork", False)),
        "created_at": _isoformat(getattr(repo, "created_at", None)),
        "updated_at": _isoformat(getattr(repo, "updated_at", None)),
        "pushed_at": _isoformat(getattr(repo, "pushed_at", None)),
        "html_url": repo.html_url,
        "clone_url": getattr(repo, "clone_url", None),
        "ssh_url": getattr(repo, "ssh_url", None),
        "default_branch": getattr(repo, "default_branch", None),
        "description": getattr(repo, "description", None),
    }


def _safe_count(factory) -> Optional[int]:
    try:
        return int(factory().totalCount)
    except Exception:
        return None


def _repo_sort_key(item: dict, sort: str):
    if sort in {"updated", "created", "pushed"}:
        return _parse_time(item.get(f"{sort}_at"))
    if sort == "stars":
        return int(item.get("stars") or 0)
    if sort == "open-prs":
        return int(item.get("open_prs") or 0)
    if sort == "open-issues":
        return int(item.get("open_issues") or 0)
    return str(item.get("name") or item.get("full_name") or "").lower()


def _parse_time(value: Optional[str]) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def get_pr_checks(
    client,
    repo: str,
    number: int,
    check_limit: int,
    workflow_limit: int,
) -> dict:
    repo_obj = client.get_repo(repo)
    pr = repo_obj.get_pull(number)
    commit = repo_obj.get_commit(pr.head.sha)
    return _build_pr_check_payload(
        pr,
        commit,
        repo_obj,
        check_limit=check_limit,
        workflow_limit=workflow_limit,
    )


def post_pr_create(client, repo: str, base: str, head: str, title: str, body: str) -> dict:
    repo_obj = client.get_repo(repo)
    pr = repo_obj.create_pull(title=title, body=body, base=base, head=head)
    return _build_pr_view_payload(pr)


def post_pr_comment(client, repo: str, number: int, body: str) -> dict:
    repo_obj = client.get_repo(repo)
    pr = repo_obj.get_pull(number)
    comment = pr.create_issue_comment(body)
    return {
        "url": comment.html_url,
        "body": comment.body,
        "id": getattr(comment, "id", None),
    }


def post_pr_merge(
    client,
    repo: str,
    number: int,
    method: str,
    title: Optional[str],
    message: Optional[str],
) -> dict:
    repo_obj = client.get_repo(repo)
    pr = repo_obj.get_pull(number)
    payload = {"merge_method": method}
    if title is not None:
        payload["commit_title"] = title
    if message is not None:
        payload["commit_message"] = message
    result = pr.merge(**payload)
    return {
        "merged": result.merged,
        "message": result.message,
        "url": pr.html_url,
    }


def patch_pr_edit(
    client,
    repo: str,
    number: int,
    *,
    title: Optional[str],
    body: Optional[str],
    state: Optional[str],
    base: Optional[str],
) -> dict:
    repo_obj = client.get_repo(repo)
    pr = repo_obj.get_pull(number)
    payload = {}
    if title is not None:
        payload["title"] = title
    if body is not None:
        payload["body"] = body
    if state is not None:
        payload["state"] = state
    if base is not None:
        payload["base"] = base
    pr.edit(**payload)
    return _build_pr_view_payload(pr)


def get_repo_permissions(repo: str, token: Optional[str]) -> dict:
    return github_api_get_json(repo, "", token)


def get_run_view(repo: str, run_id: int, token: Optional[str], job_limit: int) -> dict:
    run_payload = github_api_get_json(repo, f"/actions/runs/{run_id}", token)
    jobs_payload = github_api_get_json(
        repo,
        f"/actions/runs/{run_id}/jobs",
        token,
        params={"per_page": min(max(job_limit, 1), 100)},
    )
    return _build_workflow_run_payload(run_payload, jobs_payload, job_limit=job_limit)


def get_job_logs(repo: str, job_id: int, token: Optional[str]) -> dict:
    job_payload = github_api_get_json(repo, f"/actions/jobs/{job_id}", token)
    logs_text = github_api_get_text(repo, f"/actions/jobs/{job_id}/logs", token)
    return {
        "job": _build_workflow_job_payload(job_payload),
        "log": logs_text,
    }


def _build_pr_view_payload(pr) -> dict:
    return {
        "number": pr.number,
        "title": pr.title,
        "state": pr.state,
        "url": pr.html_url,
        "author": pr.user.login if pr.user else None,
        "created_at": _isoformat(getattr(pr, "created_at", None)),
        "updated_at": _isoformat(getattr(pr, "updated_at", None)),
        "merged_at": _isoformat(getattr(pr, "merged_at", None)),
        "base": pr.base.ref if pr.base else None,
        "head": pr.head.ref if pr.head else None,
        "head_sha": pr.head.sha if pr.head else None,
        "mergeable": getattr(pr, "mergeable", None),
        "mergeable_state": getattr(pr, "mergeable_state", None),
    }


def _build_pr_check_payload(
    pr,
    commit,
    repo_obj,
    check_limit: int,
    workflow_limit: int,
) -> dict:
    payload = _build_pr_view_payload(pr)
    statuses = []
    try:
        combined_status = commit.get_combined_status()
        for status in combined_status.statuses:
            statuses.append(
                {
                    "context": status.context,
                    "state": status.state,
                    "description": status.description,
                    "target_url": status.target_url,
                    "updated_at": _isoformat(status.updated_at),
                }
            )
        combined_status_payload = {
            "state": combined_status.state,
            "sha": combined_status.sha,
            "total_count": combined_status.total_count,
            "statuses": statuses,
        }
    except Exception as exc:
        combined_status_payload = {
            "state": "unavailable",
            "sha": getattr(pr.head, "sha", None),
            "total_count": 0,
            "statuses": [],
            "error": str(exc),
        }

    check_runs = []
    check_runs_error = None
    try:
        for check_run in commit.get_check_runs():
            check_runs.append(
                {
                    "name": check_run.name,
                    "status": check_run.status,
                    "conclusion": check_run.conclusion,
                    "details_url": check_run.details_url,
                    "html_url": getattr(check_run, "html_url", None),
                    "app": check_run.app.name if getattr(check_run, "app", None) else None,
                    "started_at": _isoformat(check_run.started_at),
                    "completed_at": _isoformat(check_run.completed_at),
                }
            )
            if len(check_runs) >= check_limit:
                break
    except Exception as exc:
        check_runs_error = str(exc)

    workflow_runs = []
    workflow_runs_error = None
    try:
        for workflow_run in repo_obj.get_workflow_runs(head_sha=pr.head.sha):
            workflow_runs.append(
                {
                    "name": workflow_run.name,
                    "display_title": workflow_run.display_title,
                    "event": workflow_run.event,
                    "status": workflow_run.status,
                    "conclusion": workflow_run.conclusion,
                    "html_url": workflow_run.html_url,
                    "created_at": _isoformat(workflow_run.created_at),
                    "updated_at": _isoformat(workflow_run.updated_at),
                    "run_started_at": _isoformat(
                        getattr(workflow_run, "run_started_at", None)
                    ),
                    "head_branch": workflow_run.head_branch,
                    "head_sha": workflow_run.head_sha,
                    "run_number": workflow_run.run_number,
                }
            )
            if len(workflow_runs) >= workflow_limit:
                break
    except Exception as exc:
        workflow_runs_error = str(exc)

    payload["combined_status"] = combined_status_payload
    payload["check_runs"] = check_runs
    payload["check_runs_error"] = check_runs_error
    payload["workflow_runs"] = workflow_runs
    payload["workflow_runs_error"] = workflow_runs_error
    return payload


def _build_workflow_run_payload(
    run_payload: dict,
    jobs_payload: dict,
    job_limit: int,
) -> dict:
    jobs = [
        _build_workflow_job_payload(job_payload)
        for job_payload in jobs_payload.get("jobs", [])[:job_limit]
    ]
    return {
        "id": run_payload["id"],
        "name": run_payload.get("name"),
        "display_title": run_payload.get("display_title"),
        "event": run_payload.get("event"),
        "status": run_payload.get("status"),
        "conclusion": run_payload.get("conclusion"),
        "html_url": run_payload.get("html_url"),
        "created_at": run_payload.get("created_at"),
        "updated_at": run_payload.get("updated_at"),
        "run_started_at": run_payload.get("run_started_at"),
        "head_branch": run_payload.get("head_branch"),
        "head_sha": run_payload.get("head_sha"),
        "run_number": run_payload.get("run_number"),
        "jobs": jobs,
        "jobs_total_count": jobs_payload.get("total_count", len(jobs)),
    }


def _build_workflow_job_payload(job_payload: dict) -> dict:
    return {
        "id": job_payload["id"],
        "name": job_payload.get("name"),
        "status": job_payload.get("status"),
        "conclusion": job_payload.get("conclusion"),
        "html_url": job_payload.get("html_url"),
        "runner_name": job_payload.get("runner_name"),
        "runner_group_name": job_payload.get("runner_group_name"),
        "labels": job_payload.get("labels") or [],
        "started_at": job_payload.get("started_at"),
        "completed_at": job_payload.get("completed_at"),
        "steps": [
            {
                "number": step.get("number"),
                "name": step.get("name"),
                "status": step.get("status"),
                "conclusion": step.get("conclusion"),
            }
            for step in job_payload.get("steps", [])
        ],
    }


def _isoformat(value) -> Optional[str]:
    return value.isoformat() if value else None

from __future__ import annotations

import json
import re
from typing import Any

import click


JSON_FIELD_ALIASES = {
    "baseRefName": "base",
    "createdAt": "created_at",
    "defaultBranchRef": "default_branch",
    "headRefName": "head",
    "headRefOid": "head_sha",
    "htmlUrl": "html_url",
    "isArchived": "archived",
    "isFork": "fork",
    "isPrivate": "private",
    "mergeStateStatus": "mergeable_state",
    "mergedAt": "merged_at",
    "updatedAt": "updated_at",
}


def echo_json_payload(payload: Any, fields: str | None, *, default=str) -> None:
    click.echo(json.dumps(project_json_payload(payload, fields), ensure_ascii=False, indent=2, default=default))


def echo_json_if_requested(
    payload: Any,
    fields: str | None,
    json_output: bool,
    *,
    default=str,
) -> bool:
    if fields is not None and json_output:
        raise click.ClickException("Use either --json or --json-output, not both")
    if fields is not None:
        echo_json_payload(payload, fields, default=default)
        return True
    if json_output:
        echo_json_payload(payload, None, default=default)
        return True
    return False


def project_json_payload(payload: Any, fields: str | None) -> Any:
    parsed_fields = parse_json_fields(fields)
    if not parsed_fields:
        return payload
    if isinstance(payload, list):
        return [_project_json_object(item, parsed_fields) for item in payload]
    return _project_json_object(payload, parsed_fields)


def parse_json_fields(fields: str | None) -> list[str]:
    if fields is None:
        return []
    parsed = [field.strip() for field in fields.split(",") if field.strip()]
    if not parsed:
        raise click.ClickException("--json requires a comma-separated field list")
    return parsed


def _project_json_object(item: Any, fields: list[str]) -> dict:
    if not isinstance(item, dict):
        raise click.ClickException("--json field selection requires object payloads")
    projected = {}
    missing = []
    for field in fields:
        sentinel = object()
        value = _lookup_json_field(item, field, sentinel)
        if value is sentinel:
            missing.append(field)
        else:
            projected[field] = value
    if missing:
        available = ", ".join(sorted(item.keys()))
        raise click.ClickException(
            f"Unknown JSON field(s): {', '.join(missing)}. Available fields: {available}"
        )
    return projected


def _lookup_json_field(item: dict, field: str, default: Any) -> Any:
    candidates = [field]
    alias = JSON_FIELD_ALIASES.get(field)
    if alias:
        candidates.append(alias)
    snake = _camel_to_snake(field)
    if snake != field:
        candidates.append(snake)
    for candidate in candidates:
        if candidate in item:
            return item[candidate]
    return default


def _camel_to_snake(value: str) -> str:
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value).lower()


def derive_repo_capabilities(permissions: dict) -> dict:
    pull = bool(permissions.get("pull"))
    push = bool(permissions.get("push"))
    admin = bool(permissions.get("admin"))
    maintain = bool(permissions.get("maintain"))
    triage = bool(permissions.get("triage"))
    return {
        "can_read_pr": pull,
        "can_comment_pr": triage or push or maintain or admin,
        "can_merge_pr": push or maintain or admin,
        "can_view_checks": pull,
        "can_view_actions": pull,
    }


def echo_pr_list(items: list[dict]) -> None:
    if not items:
        click.echo("No pull requests found.")
        return
    for item in items:
        click.echo(f"#{item['number']} [{item['state']}] {item['title']} ({item['author']})")
        click.echo(f"  {item['url']}")


def echo_pr_view(payload: dict) -> None:
    click.echo(f"#{payload['number']} [{payload['state']}] {payload['title']}")
    click.echo(f"Author: {payload['author']}")
    click.echo(f"URL: {payload['url']}")
    click.echo(f"Base: {payload['base']}  Head: {payload['head']}")
    click.echo(
        f"Mergeable: {format_optional(payload['mergeable'])}  "
        f"Merge State: {format_optional(payload['mergeable_state'])}"
    )
    click.echo(f"Created: {payload['created_at']}  Updated: {payload['updated_at']}")
    click.echo(f"Merged: {payload['merged_at']}")


def echo_pr_checks(payload: dict) -> None:
    click.echo(f"#{payload['number']} [{payload['state']}] {payload['title']}")
    click.echo(f"Author: {payload['author']}")
    click.echo(f"URL: {payload['url']}")
    click.echo(f"Base: {payload['base']}  Head: {payload['head']}")
    click.echo(f"Head SHA: {payload['head_sha']}")
    click.echo(
        f"Mergeable: {format_optional(payload['mergeable'])}  "
        f"Merge State: {format_optional(payload['mergeable_state'])}"
    )

    combined = payload["combined_status"]
    click.echo(
        f"Combined status: {combined['state']} "
        f"({combined['total_count']} status{'es' if combined['total_count'] != 1 else ''})"
    )
    if combined.get("error"):
        click.echo(f"  note: {combined['error']}")

    if combined["statuses"]:
        click.echo("Statuses:")
        for status in combined["statuses"]:
            desc = f" - {status['description']}" if status["description"] else ""
            click.echo(f"  - {status['context']}: {status['state']}{desc}")
            if status["target_url"]:
                click.echo(f"    {status['target_url']}")
    else:
        click.echo("Statuses: none")

    if payload["check_runs"]:
        click.echo("Check runs:")
        for check_run in payload["check_runs"]:
            conclusion = check_run["conclusion"] or "-"
            app = f" [{check_run['app']}]" if check_run["app"] else ""
            click.echo(
                f"  - {check_run['name']}: {check_run['status']}/{conclusion}{app}"
            )
            if check_run["details_url"]:
                click.echo(f"    {check_run['details_url']}")
    else:
        if payload.get("check_runs_error"):
            click.echo("Check runs: unavailable")
            click.echo(f"  note: {payload['check_runs_error']}")
        else:
            click.echo("Check runs: none")

    if payload["workflow_runs"]:
        click.echo("Workflow runs:")
        for workflow_run in payload["workflow_runs"]:
            conclusion = workflow_run["conclusion"] or "-"
            click.echo(
                f"  - {workflow_run['name']}: {workflow_run['status']}/{conclusion} "
                f"(event={workflow_run['event']}, run={workflow_run['run_number']})"
            )
            if workflow_run["html_url"]:
                click.echo(f"    {workflow_run['html_url']}")
    else:
        if payload.get("workflow_runs_error"):
            click.echo("Workflow runs: unavailable")
            click.echo(f"  note: {payload['workflow_runs_error']}")
        else:
            click.echo("Workflow runs: none")


def echo_workflow_run(payload: dict) -> None:
    conclusion = payload["conclusion"] or "-"
    click.echo(
        f"Run #{payload['run_number']} (id={payload['id']}): "
        f"{payload['status']}/{conclusion}"
    )
    click.echo(f"Name: {payload['name']}")
    click.echo(f"Title: {payload['display_title']}")
    click.echo(f"Event: {payload['event']}")
    click.echo(f"URL: {payload['html_url']}")
    click.echo(f"Branch: {payload['head_branch']}")
    click.echo(f"Head SHA: {payload['head_sha']}")

    if payload["jobs"]:
        click.echo(f"Jobs ({len(payload['jobs'])}/{payload['jobs_total_count']} shown):")
        for job in payload["jobs"]:
            echo_workflow_job(job, prefix="  - ")
    else:
        click.echo("Jobs: none")


def echo_workflow_job(payload: dict, prefix: str = "") -> None:
    conclusion = payload["conclusion"] or "-"
    click.echo(
        f"{prefix}{payload['name']} (id={payload['id']}): {payload['status']}/{conclusion}"
    )
    if payload["html_url"]:
        click.echo(f"{prefix}  {payload['html_url']}")
    runner_bits = [
        bit for bit in [payload["runner_name"], payload["runner_group_name"]] if bit
    ]
    if runner_bits:
        click.echo(f"{prefix}  runner: {' / '.join(runner_bits)}")
    if payload["labels"]:
        click.echo(f"{prefix}  labels: {', '.join(payload['labels'])}")
    if payload["steps"]:
        click.echo(f"{prefix}  steps:")
        for step in payload["steps"]:
            step_conclusion = step["conclusion"] or "-"
            click.echo(
                f"{prefix}    - [{step['number']}] {step['name']}: {step['status']}/{step_conclusion}"
            )


def collect_merge_blockers(payload: dict) -> list[str]:
    blockers: list[str] = []
    if payload["mergeable"] is False:
        blockers.append("pull request is not mergeable against the current base branch")

    merge_state = payload["mergeable_state"]
    if merge_state in {"dirty", "blocked", "behind", "draft", "unknown"}:
        blockers.append(f"pull request merge state is {merge_state}")

    for status in payload["combined_status"]["statuses"]:
        if status["state"] != "success":
            blockers.append(f"status {status['context']} is {status['state']}")

    for check_run in payload["check_runs"]:
        status = check_run["status"]
        conclusion = check_run["conclusion"]
        if status != "completed":
            blockers.append(f"check run {check_run['name']} is {status}")
            continue
        if conclusion not in {"success", "neutral", "skipped"}:
            blockers.append(
                f"check run {check_run['name']} concluded {conclusion or 'unknown'}"
            )

    for workflow_run in payload["workflow_runs"]:
        status = workflow_run["status"]
        conclusion = workflow_run["conclusion"]
        if status != "completed":
            blockers.append(f"workflow {workflow_run['name']} is {status}")
            continue
        if conclusion not in {"success", "neutral", "skipped"}:
            blockers.append(
                f"workflow {workflow_run['name']} concluded {conclusion or 'unknown'}"
            )

    return blockers


def has_incomplete_pr_checks(payload: dict) -> bool:
    for status in payload["combined_status"]["statuses"]:
        if status["state"] == "pending":
            return True
    for check_run in payload["check_runs"]:
        if check_run["status"] != "completed":
            return True
    for workflow_run in payload["workflow_runs"]:
        if workflow_run["status"] != "completed":
            return True
    return False


def format_optional(value) -> str:
    return "-" if value is None else str(value)


def tail_text(text: str, tail: int) -> str:
    if tail == 0:
        return text
    lines = text.splitlines()
    if len(lines) <= tail:
        return text
    return "\n".join(lines[-tail:])

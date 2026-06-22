"""Auxiliary GitHub CLI commands for Actions and credentials.

Pull request commands live in ``chatgh.commands.pr``. This module keeps
non-PR GitHub tasks available as first-class command groups.
"""

from __future__ import annotations

import json

import click
from chatstyle import CommandField, CommandSchema, add_interactive_option, resolve_command_inputs
from chatstyle.core import InteractiveResolution, normalize_interactive
from chatstyle.core.interactive import is_interactive_available
from chatstyle.tui.prompt import BACK_VALUE, ask_text

from chatgh.github.api import resolve_repo_from_git_remote, resolve_token
from chatgh.github.commands import (
    create_repo,
    inspect_repo_protection,
    list_repo_protections,
    list_repos,
    repo_perms,
    set_token,
    view_job_logs,
    view_run,
)
from chatgh.github.render import echo_workflow_job, echo_workflow_run, format_optional


def _mask_secret(value: str) -> str:
    if len(value) <= 8:
        return value[:2] + "..." + value[-2:]
    return value[:6] + "..." + value[-4:]

RUN_ID_SCHEMA = CommandSchema(
    name="run-id",
    fields=(CommandField("run_id", prompt="workflow run id", kind="int", required=True),),
)

JOB_ID_SCHEMA = CommandSchema(
    name="job-id",
    fields=(CommandField("job_id", prompt="workflow job id", kind="int", required=True),),
)

OWNER_SCHEMA = CommandSchema(
    name="repo-owner",
    fields=(CommandField("owner", prompt="GitHub owner or organization", required=True),),
)

REPO_CREATE_SCHEMA = CommandSchema(
    name="repo-create",
    fields=(
        CommandField("owner", prompt="GitHub owner or organization", required=True),
        CommandField("name", prompt="repository name", required=True),
    ),
)


class _TextPromptRuntime:
    def ask_text(self, prompt: str, default: str = "", password: bool = False):
        return ask_text(prompt, default=default, password=password)


TEXT_PROMPT_RUNTIME = _TextPromptRuntime()


def resolve_cli_interactive_mode(interactive: bool | None, *, auto_prompt_condition: bool):
    interactive = normalize_interactive(interactive)
    can_prompt = is_interactive_available()
    force_interactive = interactive is True
    need_prompt = force_interactive or (
        interactive is None and auto_prompt_condition and can_prompt
    )
    return InteractiveResolution(
        interactive=interactive,
        can_prompt=can_prompt,
        force_interactive=force_interactive,
        need_prompt=need_prompt,
    )


@click.group(name="github-extra")
def cli() -> None:
    """GitHub Actions and credential helpers."""


@cli.group(name="run")
def run_group() -> None:
    """GitHub Actions helpers."""


@cli.group(name="repo")
def repo_group() -> None:
    """Repository helpers."""


@repo_group.command(name="list")
@click.option("--owner", required=False, help="GitHub owner or organization.")
@click.option("--limit", default=50, type=click.IntRange(min=1), show_default=True)
@click.option(
    "--sort",
    type=click.Choice(["updated", "created", "pushed", "name", "stars", "open-prs", "open-issues"]),
    default="updated",
    show_default=True,
    help="Sort repositories before applying --limit.",
)
@click.option("--direction", type=click.Choice(["asc", "desc"]), default="desc", show_default=True)
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def repo_list(owner, limit, sort, direction, json_output, token, interactive):
    """List repositories for an owner or organization."""
    inputs = resolve_command_inputs(
        schema=OWNER_SCHEMA,
        provided={"owner": owner},
        interactive=interactive,
        usage="Usage: chatgh repo list --owner TEXT [-i|-I]",
        prompt_runtime_override=TEXT_PROMPT_RUNTIME,
        interactive_resolver_override=resolve_cli_interactive_mode,
    )
    payload = list_repos(inputs["owner"], limit, sort, direction, token)
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    _echo_repo_table(payload)


def _echo_repo_table(items: list[dict]) -> None:
    columns = [
        ("repo", "full_name"),
        ("vis", "visibility"),
        ("stars", "stars"),
        ("prs", "open_prs"),
        ("issues", "open_issues"),
        ("updated", "updated_at"),
        ("created", "created_at"),
    ]
    rows = []
    for item in items:
        row = []
        for _, key in columns:
            value = item.get(key)
            if key.endswith("_at"):
                value = str(value or "")[:10]
            row.append(str(value if value is not None else ""))
        rows.append(row)
    widths = [len(label) for label, _ in columns]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = min(max(widths[index], len(value)), 48)
    header = "  ".join(label.ljust(widths[index]) for index, (label, _) in enumerate(columns))
    click.echo(header)
    click.echo("  ".join("-" * width for width in widths))
    for row in rows:
        clipped = [value[: widths[index]] for index, value in enumerate(row)]
        click.echo("  ".join(value.ljust(widths[index]) for index, value in enumerate(clipped)))


@repo_group.command(name="protection")
@click.option("--repo", default=None, help="Repository in owner/name form. Defaults to current git remote when --owner is omitted.")
@click.option("--owner", default=None, help="GitHub owner or organization for inventory mode.")
@click.option("--limit", default=50, type=click.IntRange(min=1), show_default=True)
@click.option("--jobs", default=8, type=click.IntRange(min=1), show_default=True, help="Concurrent protection checks in owner inventory mode.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def repo_protection(repo, owner, limit, jobs, json_output, token):
    """Show default-branch protection and ruleset status."""
    if repo and owner:
        raise click.ClickException("Use either --repo for one repository or --owner for inventory, not both.")
    if owner:
        payload = list_repo_protections(owner, limit, token, jobs)
        if json_output:
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        _echo_repo_protection_table(payload)
        return

    if repo is None:
        repo, _ = resolve_repo_from_git_remote()
    payload = inspect_repo_protection(repo, token)
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    _echo_repo_protection_summary(payload)


def _yes_no(value) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def _compact_error(error: object) -> str:
    text = str(error)
    text = text.replace("GitHub API error (403) for /rulesets: ", "")
    text = text.replace(". If this repository should use a dedicated token, run `chatgh set-token` inside the repo to add a matching git credential entry.", "")
    return text


def _echo_repo_protection_summary(payload: dict) -> None:
    protection = payload.get("branch_protection") or {}
    click.echo(f"Repo: {payload.get('repo')}")
    click.echo(f"Default Branch: {payload.get('default_branch') or ''}")
    click.echo(f"Protected: {_yes_no(payload.get('default_branch_protected'))}")
    click.echo(f"PR Required: {_yes_no(protection.get('required_pull_request_reviews'))}")
    reviews = protection.get("required_approving_review_count")
    click.echo(f"Reviews Required: {'' if reviews is None else reviews}")
    click.echo(f"Force Pushes Allowed: {_yes_no(protection.get('allow_force_pushes'))}")
    click.echo(f"Deletions Allowed: {_yes_no(protection.get('allow_deletions'))}")
    click.echo(f"Rulesets: {payload.get('ruleset_count', 0)}")
    for ruleset in payload.get("rulesets") or []:
        name = ruleset.get("name") or ruleset.get("id") or "<unnamed>"
        click.echo(f"  - {name}: {ruleset.get('enforcement') or 'unknown'}")
    for error in payload.get("errors") or []:
        click.echo(f"Warning: {error}", err=True)


def _echo_repo_protection_table(items: list[dict]) -> None:
    columns = [
        ("repo", "repo"),
        ("branch", "default_branch"),
        ("protected", "default_branch_protected"),
        ("reviews", "required_approving_review_count"),
        ("rulesets", "ruleset_count"),
        ("error", "error_summary"),
    ]
    rows = []
    for item in items:
        protection = item.get("branch_protection") or {}
        errors = item.get("errors") or []
        row_values = {
            "repo": item.get("repo"),
            "default_branch": item.get("default_branch"),
            "default_branch_protected": _yes_no(item.get("default_branch_protected")),
            "required_approving_review_count": protection.get("required_approving_review_count"),
            "ruleset_count": item.get("ruleset_count", 0),
            "error_summary": "; ".join(_compact_error(error) for error in errors),
        }
        rows.append([str(row_values.get(key) if row_values.get(key) is not None else "") for _, key in columns])
    widths = [len(label) for label, _ in columns]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = min(max(widths[index], len(value)), 48)
    click.echo("  ".join(label.ljust(widths[index]) for index, (label, _) in enumerate(columns)))
    click.echo("  ".join("-" * width for width in widths))
    for row in rows:
        clipped = [value[: widths[index]] for index, value in enumerate(row)]
        click.echo("  ".join(value.ljust(widths[index]) for index, value in enumerate(clipped)))


@repo_group.command(name="create")
@click.option("--owner", required=False, help="GitHub owner or organization.")
@click.option("--name", required=False, help="Repository name.")
@click.option("--description", default=None, help="Repository description.")
@click.option("--public", "public_repo", is_flag=True, help="Create a public repository. Defaults to private.")
@click.option("--if-exists", type=click.Choice(["error", "use"]), default="error", show_default=True)
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def repo_create(owner, name, description, public_repo, if_exists, json_output, token, interactive):
    """Create a repository. Repositories are private by default."""
    inputs = resolve_command_inputs(
        schema=REPO_CREATE_SCHEMA,
        provided={"owner": owner, "name": name},
        interactive=interactive,
        usage="Usage: chatgh repo create --owner TEXT --name TEXT [-i|-I]",
        prompt_runtime_override=TEXT_PROMPT_RUNTIME,
        interactive_resolver_override=resolve_cli_interactive_mode,
    )
    payload = create_repo(inputs["owner"], inputs["name"], not public_repo, description, if_exists, token)
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    created = "created" if payload.get("created") else "existing"
    private = "private" if payload.get("private") else "public"
    click.echo(f"{created}: {payload['full_name']} ({private})")
    if payload.get("html_url"):
        click.echo(payload["html_url"])


@run_group.command(name="view")
@click.option("--repo", required=False, help="Repository in owner/name form.")
@click.option("--run-id", required=False, type=int, help="Workflow run id.")
@click.option("--job-limit", default=50, type=int, show_default=True, help="Max jobs to show.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def run_view(repo, run_id, job_limit, json_output, token, interactive):
    """Show a workflow run and its jobs."""
    inputs = resolve_command_inputs(
        schema=RUN_ID_SCHEMA,
        provided={"run_id": run_id},
        interactive=interactive,
        usage="Usage: chatgh run view [--repo TEXT] --run-id INTEGER [-i|-I]",
    )
    payload = view_run(repo, inputs["run_id"], job_limit, token)
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    echo_workflow_run(payload)


@run_group.command(name="logs")
@click.option("--repo", required=False, help="Repository in owner/name form.")
@click.option("--job-id", required=False, type=int, help="Workflow job id.")
@click.option("--tail", default=200, type=click.IntRange(min=0), show_default=True)
@click.option("--output", type=click.Path(dir_okay=False, writable=True), default=None)
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def run_logs(repo, job_id, tail, output, json_output, token, interactive):
    """Show logs for a workflow job."""
    inputs = resolve_command_inputs(
        schema=JOB_ID_SCHEMA,
        provided={"job_id": job_id},
        interactive=interactive,
        usage="Usage: chatgh run logs [--repo TEXT] --job-id INTEGER [-i|-I]",
    )
    payload = view_job_logs(repo, inputs["job_id"], tail, output, token)
    if json_output:
        click.echo(
            json.dumps(
                {
                    "job": payload["job"],
                    "tail": payload["tail"],
                    "output_path": payload["output_path"],
                    "log": payload["log"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    echo_workflow_job(payload["job"])
    if output:
        click.echo(f"Saved full log to: {output}")
    click.echo("Log:")
    click.echo(payload["rendered_log"])


@cli.command(name="repo-perms")
@click.option("--repo", required=False, help="Repository in owner/name form.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--full-json", is_flag=True, help="Include the full repository payload.")
@click.option("--token", default=None, help="GitHub token.")
def repo_permissions(repo, json_output, full_json, token):
    """Show repository permissions for the current token."""
    payload = repo_perms(repo, full_json, token)
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(f"Repo: {payload['repo']}")
    click.echo(f"Private: {format_optional(payload['private'])}")
    click.echo(f"Visibility: {format_optional(payload['visibility'])}")
    click.echo(f"Token: {payload['token_mask']}")
    click.echo(f"Token Source: {payload['token_source']}")
    click.echo("Permissions:")
    if not payload["permissions"]:
        click.echo("  - none returned")
    else:
        for key in sorted(payload["permissions"]):
            click.echo(f"  - {key}: {payload['permissions'][key]}")
    click.echo("Capabilities:")
    for key, value in payload["capabilities"].items():
        click.echo(f"  - {key}: {value}")


@cli.command(name="set-token")
@click.option("--token", default=None, help="GitHub token.")
@click.option("--save-env", is_flag=True, help="Also save the token into ChatGH env config.")
def set_repo_token(token, save_env):
    """Configure HTTPS credentials for the current GitHub repository."""
    from chatgh.github.commands import resolve_repo_and_credential_path

    repo, credential_path = resolve_repo_and_credential_path(None)
    resolved_token = resolve_token(token, credential_path=credential_path, exact_only=True)
    if resolved_token is None:
        resolved_token = resolve_token(token, credential_path=credential_path)
    if is_interactive_available():
        prompt_label = "github_token"
        if resolved_token:
            prompt_label += f" (current: {_mask_secret(resolved_token)}, enter to keep)"
        token_input = ask_text(prompt_label, password=True)
        if token_input == BACK_VALUE:
            raise click.Abort()
        entered = str(token_input).strip()
        if entered:
            resolved_token = entered
    result = set_token(resolved_token, save_env)
    click.echo(f"Configured Git HTTPS token for {result['repo']}.")
    if result["saved_env"]:
        click.echo("Saved token to ChatGH env config.")

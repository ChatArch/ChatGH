"""Auxiliary GitHub CLI commands for Actions and credentials.

Pull request commands live in ``chatgh.commands.pr``. This module keeps
non-PR GitHub tasks available as first-class command groups.
"""

from __future__ import annotations

import json

import click
from chatstyle import CommandField, CommandSchema, add_interactive_option, resolve_command_inputs
from chatstyle.core.interactive import is_interactive_available
from chatstyle.tui.prompt import BACK_VALUE, ask_text

from chatgh.github.api import resolve_token
from chatgh.github.commands import repo_perms, set_token, view_job_logs, view_run
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


@click.group(name="github-extra")
def cli() -> None:
    """GitHub Actions and credential helpers."""


@cli.group(name="run")
def run_group() -> None:
    """GitHub Actions helpers."""


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

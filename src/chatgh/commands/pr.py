"""chatgh pr — pull request commands with gh-style arguments.

Heavy GitHub helpers are imported inside command callbacks so that
`chatgh --help` stays fast.
"""

from __future__ import annotations

import json

import click
from chatstyle import (
    CommandField,
    CommandSchema,
    add_interactive_option,
    resolve_command_inputs,
)


PR_CREATE_SCHEMA = CommandSchema(
    name="pr-create",
    fields=(
        CommandField("base", prompt="base branch", required=True),
        CommandField("head", prompt="head branch", required=True),
        CommandField("title", prompt="title", required=True),
    ),
)

PR_NUMBER_SCHEMA = CommandSchema(
    name="pr-number",
    fields=(CommandField("number", prompt="pr number", kind="int", required=True),),
)


@click.group(name="pr")
def pr_group() -> None:
    """Pull request helpers."""


# ── list ──────────────────────────────────────────────────────────────────────

@pr_group.command("list")
@click.option("--repo", default=None, help="owner/name (reads CHATGH_DEFAULT_REPO if omitted)")
@click.option("--state", default="open", type=click.Choice(["open", "closed", "all"]), show_default=True)
@click.option("--limit", default=20, type=int, show_default=True)
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
def pr_list(repo: str | None, state: str, limit: int, json_output: bool, token: str | None) -> None:
    """List pull requests."""
    from chatgh.github.commands import list_prs
    from chatgh.github.render import echo_pr_list

    prs = list_prs(repo, state, limit, token)

    if json_output:
        click.echo(json.dumps(prs, ensure_ascii=False, indent=2, default=str))
        return

    if not prs:
        click.echo("No pull requests found.")
        return
    echo_pr_list(prs)


# ── view ──────────────────────────────────────────────────────────────────────

@pr_group.command("view")
@click.argument("number", required=False, type=int)
@click.option("--repo", default=None)
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
@add_interactive_option
def pr_view(repo: str | None, number: int | None, json_output: bool, token: str | None, interactive: bool | None) -> None:
    """Show pull request details."""
    from chatgh.github.commands import view_pr
    from chatgh.github.render import echo_pr_view

    inputs = resolve_command_inputs(
        schema=PR_NUMBER_SCHEMA,
        provided={"number": number},
        interactive=interactive,
        usage="Usage: chatgh pr view NUMBER [--repo TEXT] [-i|-I]",
    )
    payload = view_pr(repo, int(inputs["number"]), token)

    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return

    echo_pr_view(payload)


# ── checks ────────────────────────────────────────────────────────────────────

@pr_group.command("checks")
@click.argument("number", required=False, type=int)
@click.option("--repo", default=None)
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
@add_interactive_option
def pr_checks(repo: str | None, number: int | None, json_output: bool, token: str | None, interactive: bool | None) -> None:
    """Show CI check status for a pull request."""
    from chatgh.github.commands import check_pr
    from chatgh.github.render import echo_pr_checks

    inputs = resolve_command_inputs(
        schema=PR_NUMBER_SCHEMA,
        provided={"number": number},
        interactive=interactive,
        usage="Usage: chatgh pr checks NUMBER [--repo TEXT] [-i|-I]",
    )
    payload = check_pr(
        repo,
        int(inputs["number"]),
        check_limit=20,
        workflow_limit=10,
        wait_for_completion=False,
        interval=15,
        timeout=None,
        token=token,
    )

    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return

    echo_pr_checks(payload)


# ── helpers ───────────────────────────────────────────────────────────────────

def _resolve_repo(repo: str | None) -> tuple[str, str]:
    """Parse 'owner/name' or fall back to CHATGH_DEFAULT_REPO."""
    if repo:
        parts = repo.strip().split("/", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
    # try chatenv default
    try:
        from chatenv import get_paths
        from chatgh.config import GitHubConfig
        GitHubConfig.load_all(get_paths().envs_dir)
        default = GitHubConfig.GITHUB_ACCESS_TOKEN.value  # not the right field, placeholder
    except Exception:
        pass

    raise click.UsageError(
        "Missing repo. Pass --repo owner/name or set CHATGH_DEFAULT_REPO via `chatenv init -t chatgh`."
    )


def _pr_to_dict(pr: object) -> dict:
    """Convert a PR model to a plain dict for JSON output."""
    if hasattr(pr, "model_dump"):
        return pr.model_dump(mode="json")
    return vars(pr)

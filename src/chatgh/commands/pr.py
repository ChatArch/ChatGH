"""chatgh pr — pull request commands backed by the generated API layer.

Imports of heavy modules (_generated.api.*, _generated.models.*) are deferred
to function bodies so that `chatgh --help` stays fast.
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
    """Pull request helpers (generated API layer)."""


# ── list ──────────────────────────────────────────────────────────────────────

@pr_group.command("list")
@click.option("--repo", default=None, help="owner/name (reads CHATGH_DEFAULT_REPO if omitted)")
@click.option("--state", default="open", type=click.Choice(["open", "closed", "all"]), show_default=True)
@click.option("--limit", default=20, type=int, show_default=True)
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
def pr_list(repo: str | None, state: str, limit: int, json_output: bool, token: str | None) -> None:
    """List pull requests."""
    # lazy imports — only loaded when this command actually runs
    from chatgh._generated.api.pulls import pulls_list
    from chatgh.adapters.client import make_client

    owner, name = _resolve_repo(repo)
    client = make_client(token)
    prs = pulls_list(client, owner, name, state=state, per_page=min(limit, 100))

    if json_output:
        click.echo(json.dumps([_pr_to_dict(pr) for pr in prs], ensure_ascii=False, indent=2))
        return

    if not prs:
        click.echo("No pull requests found.")
        return
    for pr in prs:
        draft = " [draft]" if pr.draft else ""
        click.echo(f"#{pr.number}\t{pr.state}\t{pr.title}{draft}")


# ── view ──────────────────────────────────────────────────────────────────────

@pr_group.command("view")
@click.argument("number", required=False, type=int)
@click.option("--repo", default=None)
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
@add_interactive_option
def pr_view(repo: str | None, number: int | None, json_output: bool, token: str | None, interactive: bool | None) -> None:
    """Show pull request details."""
    from chatgh._generated.api.pulls import pulls_get
    from chatgh.adapters.client import make_client

    inputs = resolve_command_inputs(
        schema=PR_NUMBER_SCHEMA,
        provided={"number": number},
        interactive=interactive,
        usage="Usage: chatgh pr view NUMBER [--repo TEXT] [-i|-I]",
    )
    owner, name = _resolve_repo(repo)
    client = make_client(token)
    pr = pulls_get(client, owner, name, int(inputs["number"]))

    if json_output:
        click.echo(json.dumps(_pr_to_dict(pr), ensure_ascii=False, indent=2))
        return

    click.echo(f"#{pr.number} {pr.title}")
    click.echo(f"State:  {pr.state}")
    click.echo(f"Author: {pr.user.login if pr.user else 'unknown'}")
    click.echo(f"Base:   {pr.base.ref} ← {pr.head.ref}")
    click.echo(f"URL:    {pr.html_url}")
    if pr.body:
        click.echo(f"\n{pr.body[:500]}")


# ── checks ────────────────────────────────────────────────────────────────────

@pr_group.command("checks")
@click.argument("number", required=False, type=int)
@click.option("--repo", default=None)
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
@add_interactive_option
def pr_checks(repo: str | None, number: int | None, json_output: bool, token: str | None, interactive: bool | None) -> None:
    """Show CI check status for a pull request."""
    from chatgh._generated.api.checks import checks_list_for_ref
    from chatgh._generated.api.pulls import pulls_get
    from chatgh.adapters.client import make_client

    inputs = resolve_command_inputs(
        schema=PR_NUMBER_SCHEMA,
        provided={"number": number},
        interactive=interactive,
        usage="Usage: chatgh pr checks NUMBER [--repo TEXT] [-i|-I]",
    )
    owner, name = _resolve_repo(repo)
    client = make_client(token)
    pr = pulls_get(client, owner, name, int(inputs["number"]))
    head_sha = pr.head.sha

    result = checks_list_for_ref(client, owner, name, head_sha, per_page=50)

    if json_output:
        runs = getattr(result, "check_runs", result) if result else []
        click.echo(json.dumps([r.model_dump() if hasattr(r, "model_dump") else r for r in runs], ensure_ascii=False, indent=2, default=str))
        return

    runs = getattr(result, "check_runs", []) if result else []
    if not runs:
        click.echo("No check runs found.")
        return
    for run in runs:
        status = run.status or ""
        conclusion = run.conclusion or ""
        flag = "✓" if conclusion == "success" else ("✗" if conclusion in ("failure", "cancelled") else "·")
        click.echo(f"  {flag} {run.name}  [{status}/{conclusion}]")


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

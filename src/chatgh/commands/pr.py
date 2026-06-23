"""chatgh pr — pull request commands with gh-style arguments.

Heavy GitHub helpers are imported inside command callbacks so that
`chatgh --help` stays fast.
"""

from __future__ import annotations

import json
from pathlib import Path

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

PR_COMMENT_SCHEMA = CommandSchema(
    name="pr-comment",
    fields=(
        CommandField("number", prompt="pr number", kind="int", required=True),
        CommandField("body", prompt="comment body", required=True),
    ),
)


@click.group(name="pr")
def pr_group() -> None:
    """Pull request helpers."""


def _resolve_body(value: str | None, file_path: Path | None) -> str:
    if value is not None and file_path is not None:
        raise click.UsageError("Pass only one of --body/--message or --body-file/--message-file.")
    if file_path is not None:
        return file_path.read_text(encoding="utf-8")
    return value or ""


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


# ── create ────────────────────────────────────────────────────────────────────

@pr_group.command("create")
@click.option("--repo", default=None, help="owner/name")
@click.option("--base", default=None, help="Base branch for the PR.")
@click.option("--head", default=None, help="Head branch for the PR.")
@click.option("--title", default=None, help="PR title.")
@click.option("--body", default=None, help="PR body text.")
@click.option("--body-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Read PR body from a file.")
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
@add_interactive_option
def pr_create(
    repo: str | None,
    base: str | None,
    head: str | None,
    title: str | None,
    body: str | None,
    body_file: Path | None,
    json_output: bool,
    token: str | None,
    interactive: bool | None,
) -> None:
    """Create a pull request."""
    from chatgh.github.commands import create_pr
    from chatgh.github.render import echo_pr_view

    inputs = resolve_command_inputs(
        schema=PR_CREATE_SCHEMA,
        provided={"base": base, "head": head, "title": title},
        interactive=interactive,
        usage="Usage: chatgh pr create --base BRANCH --head BRANCH --title TITLE [--repo TEXT] [--body TEXT|--body-file PATH] [-i|-I]",
    )
    payload = create_pr(
        repo,
        inputs["base"],
        inputs["head"],
        inputs["title"],
        _resolve_body(body, body_file),
        token,
    )

    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return

    echo_pr_view(payload)


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


# ── comment ───────────────────────────────────────────────────────────────────

@pr_group.command("comment")
@click.argument("number", required=False, type=int)
@click.option("--repo", default=None)
@click.option("--body", default=None, help="Comment body text.")
@click.option("--body-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Read comment body from a file.")
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
@add_interactive_option
def pr_comment(
    repo: str | None,
    number: int | None,
    body: str | None,
    body_file: Path | None,
    json_output: bool,
    token: str | None,
    interactive: bool | None,
) -> None:
    """Comment on a pull request."""
    from chatgh.github.commands import comment_pr

    inputs = resolve_command_inputs(
        schema=PR_COMMENT_SCHEMA,
        provided={"number": number, "body": _resolve_body(body, body_file)},
        interactive=interactive,
        usage="Usage: chatgh pr comment NUMBER --body TEXT [--repo TEXT] [-i|-I]",
    )
    payload = comment_pr(repo, int(inputs["number"]), str(inputs["body"]), token)

    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return

    click.echo(f"Commented: {payload.get('url')}")


# ── edit ──────────────────────────────────────────────────────────────────────

@pr_group.command("edit")
@click.argument("number", required=False, type=int)
@click.option("--repo", default=None)
@click.option("--title", default=None, help="New PR title.")
@click.option("--body", default=None, help="New PR body text.")
@click.option("--body-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Read new PR body from a file.")
@click.option("--state", type=click.Choice(["open", "closed"]), default=None, help="Set PR state.")
@click.option("--base", default=None, help="Change base branch.")
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
@add_interactive_option
def pr_edit(
    repo: str | None,
    number: int | None,
    title: str | None,
    body: str | None,
    body_file: Path | None,
    state: str | None,
    base: str | None,
    json_output: bool,
    token: str | None,
    interactive: bool | None,
) -> None:
    """Edit a pull request."""
    from chatgh.github.commands import edit_pr
    from chatgh.github.render import echo_pr_view

    inputs = resolve_command_inputs(
        schema=PR_NUMBER_SCHEMA,
        provided={"number": number},
        interactive=interactive,
        usage="Usage: chatgh pr edit NUMBER [--repo TEXT] [--title TEXT] [--body TEXT|--body-file PATH] [--state open|closed] [--base BRANCH] [-i|-I]",
    )
    payload = edit_pr(
        repo,
        int(inputs["number"]),
        title,
        _resolve_body(body, body_file) if (body is not None or body_file is not None) else None,
        state,
        base,
        token,
    )

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


# ── merge ─────────────────────────────────────────────────────────────────────

@pr_group.command("merge")
@click.argument("number", required=False, type=int)
@click.option("--repo", default=None)
@click.option("--method", type=click.Choice(["merge", "squash", "rebase"]), default="squash", show_default=True, help="Merge method.")
@click.option("--title", default=None, help="Merge commit title.")
@click.option("--message", default=None, help="Merge commit message.")
@click.option("--message-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Read merge commit message from a file.")
@click.option("--check/--no-check", default=True, show_default=True, help="Require green PR checks before merging.")
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
@add_interactive_option
def pr_merge(
    repo: str | None,
    number: int | None,
    method: str,
    title: str | None,
    message: str | None,
    message_file: Path | None,
    check: bool,
    json_output: bool,
    token: str | None,
    interactive: bool | None,
) -> None:
    """Merge a pull request."""
    from chatgh.github.commands import merge_pr

    inputs = resolve_command_inputs(
        schema=PR_NUMBER_SCHEMA,
        provided={"number": number},
        interactive=interactive,
        usage="Usage: chatgh pr merge NUMBER [--repo TEXT] [--method squash|merge|rebase] [--check/--no-check] [-i|-I]",
    )
    payload = merge_pr(
        repo,
        int(inputs["number"]),
        method,
        title,
        _resolve_body(message, message_file) if (message is not None or message_file is not None) else None,
        check,
        token,
    )

    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return

    click.echo(f"Merged: {payload.get('url')}")
    if payload.get("message"):
        click.echo(payload["message"])


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

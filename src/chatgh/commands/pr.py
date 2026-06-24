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



def status_prs(repo: str | None, token: str | None) -> dict:
    from chatgh.github.commands import status_prs as _status_prs
    return _status_prs(repo, token)


def diff_pr(repo: str | None, number: int, token: str | None) -> str:
    from chatgh.github.commands import diff_pr as _diff_pr
    return _diff_pr(repo, number, token)


def close_pr(repo: str | None, number: int, comment: str | None, delete_branch: bool, token: str | None) -> dict:
    from chatgh.github.commands import close_pr as _close_pr
    return _close_pr(repo, number, comment, delete_branch, token)


def reopen_pr(repo: str | None, number: int, token: str | None) -> dict:
    from chatgh.github.commands import reopen_pr as _reopen_pr
    return _reopen_pr(repo, number, token)


def review_pr(repo: str | None, number: int, event: str, body: str, token: str | None) -> dict:
    from chatgh.github.commands import review_pr as _review_pr
    return _review_pr(repo, number, event, body, token)


def ready_pr(repo: str | None, number: int, token: str | None) -> dict:
    from chatgh.github.commands import ready_pr as _ready_pr
    return _ready_pr(repo, number, token)


def update_pr_branch(repo: str | None, number: int, expected_head_sha: str | None, token: str | None) -> dict:
    from chatgh.github.commands import update_pr_branch as _update_pr_branch
    return _update_pr_branch(repo, number, expected_head_sha, token)

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



# ── status ────────────────────────────────────────────────────────────────────

@pr_group.command("status")
@click.option("--repo", default=None)
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
def pr_status(repo: str | None, json_output: bool, token: str | None) -> None:
    """Show current repository pull request status."""
    payload = status_prs(repo, token)
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    click.echo(f"Repo: {payload.get('repo')}")
    for item in payload.get("open") or []:
        click.echo(f"#{item.get('number')} {item.get('state')} {item.get('title')}")


# ── diff ──────────────────────────────────────────────────────────────────────

@pr_group.command("diff")
@click.argument("number", required=False, type=int)
@click.option("--repo", default=None)
@click.option("--token", default=None)
@add_interactive_option
def pr_diff(repo: str | None, number: int | None, token: str | None, interactive: bool | None) -> None:
    """Show a pull request diff."""
    inputs = resolve_command_inputs(
        schema=PR_NUMBER_SCHEMA,
        provided={"number": number},
        interactive=interactive,
        usage="Usage: chatgh pr diff NUMBER [--repo TEXT] [-i|-I]",
    )
    click.echo(diff_pr(repo, int(inputs["number"]), token), nl=False)


# ── close/reopen ───────────────────────────────────────────────────────────────

@pr_group.command("close")
@click.argument("number", required=False, type=int)
@click.option("--repo", default=None)
@click.option("--comment", default=None, help="Leave a closing comment before closing.")
@click.option("--delete-branch", is_flag=True, help="Record that branch deletion was requested. Does not delete a branch yet.")
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
@add_interactive_option
def pr_close(repo: str | None, number: int | None, comment: str | None, delete_branch: bool, json_output: bool, token: str | None, interactive: bool | None) -> None:
    """Close a pull request."""
    inputs = resolve_command_inputs(
        schema=PR_NUMBER_SCHEMA,
        provided={"number": number},
        interactive=interactive,
        usage="Usage: chatgh pr close NUMBER [--repo TEXT] [--comment TEXT] [-i|-I]",
    )
    payload = close_pr(repo, int(inputs["number"]), comment, delete_branch, token)
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    click.echo(f"Closed PR #{payload.get('number')}")


@pr_group.command("reopen")
@click.argument("number", required=False, type=int)
@click.option("--repo", default=None)
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
@add_interactive_option
def pr_reopen(repo: str | None, number: int | None, json_output: bool, token: str | None, interactive: bool | None) -> None:
    """Reopen a pull request."""
    inputs = resolve_command_inputs(
        schema=PR_NUMBER_SCHEMA,
        provided={"number": number},
        interactive=interactive,
        usage="Usage: chatgh pr reopen NUMBER [--repo TEXT] [-i|-I]",
    )
    payload = reopen_pr(repo, int(inputs["number"]), token)
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    click.echo(f"Reopened PR #{payload.get('number')}")


# ── review/ready/update-branch ────────────────────────────────────────────────

@pr_group.command("review")
@click.argument("number", required=False, type=int)
@click.option("--repo", default=None)
@click.option("--approve", "review_event", flag_value="APPROVE", default=False, help="Approve the pull request.")
@click.option("--request-changes", "review_event", flag_value="REQUEST_CHANGES", help="Request changes.")
@click.option("--comment", "review_event", flag_value="COMMENT", help="Submit a comment review.")
@click.option("--body", default=None, help="Review body text.")
@click.option("--body-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Read review body from a file.")
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
@add_interactive_option
def pr_review(repo: str | None, number: int | None, review_event: str | bool, body: str | None, body_file: Path | None, json_output: bool, token: str | None, interactive: bool | None) -> None:
    """Review a pull request."""
    inputs = resolve_command_inputs(
        schema=PR_NUMBER_SCHEMA,
        provided={"number": number},
        interactive=interactive,
        usage="Usage: chatgh pr review NUMBER --approve|--request-changes|--comment [--body TEXT|--body-file PATH] [-i|-I]",
    )
    event = review_event if isinstance(review_event, str) else "COMMENT"
    payload = review_pr(repo, int(inputs["number"]), event, _resolve_body(body, body_file), token)
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    click.echo(f"Submitted {event} review for PR #{payload.get('number')}")


@pr_group.command("ready")
@click.argument("number", required=False, type=int)
@click.option("--repo", default=None)
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
@add_interactive_option
def pr_ready(repo: str | None, number: int | None, json_output: bool, token: str | None, interactive: bool | None) -> None:
    """Mark a draft pull request ready for review."""
    inputs = resolve_command_inputs(
        schema=PR_NUMBER_SCHEMA,
        provided={"number": number},
        interactive=interactive,
        usage="Usage: chatgh pr ready NUMBER [--repo TEXT] [-i|-I]",
    )
    payload = ready_pr(repo, int(inputs["number"]), token)
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    click.echo(f"Marked PR #{payload.get('number')} ready for review")


@pr_group.command("update-branch")
@click.argument("number", required=False, type=int)
@click.option("--repo", default=None)
@click.option("--expected-head-sha", default=None, help="Only update if the PR head SHA still matches this value.")
@click.option("--json-output", is_flag=True)
@click.option("--token", default=None)
@add_interactive_option
def pr_update_branch(repo: str | None, number: int | None, expected_head_sha: str | None, json_output: bool, token: str | None, interactive: bool | None) -> None:
    """Update a pull request branch from its base branch."""
    inputs = resolve_command_inputs(
        schema=PR_NUMBER_SCHEMA,
        provided={"number": number},
        interactive=interactive,
        usage="Usage: chatgh pr update-branch NUMBER [--repo TEXT] [--expected-head-sha SHA] [-i|-I]",
    )
    payload = update_pr_branch(repo, int(inputs["number"]), expected_head_sha, token)
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    click.echo(f"Update-branch requested for PR #{payload.get('number')}")

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

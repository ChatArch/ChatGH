"""Click adapters for the invocation-scoped Git transport API."""

from __future__ import annotations

import json

import click

from chatgh.github.transport import fetch, pull, push, unset_token


@click.command(name="fetch")
@click.argument("remote", required=False, metavar="REMOTE")
@click.argument("refspec", required=False, metavar="REFSPEC")
@click.option("--token", default=None, help="GitHub token for this invocation.")
def fetch_command(remote: str | None, refspec: str | None, token: str | None) -> None:
    """Fetch from the current branch upstream or an explicit remote."""

    payload = fetch(remote, refspec, token)
    target = f" {payload['refspec']}" if payload["refspec"] else ""
    click.echo(f"Fetched {payload['remote']}{target}.")


@click.command(name="pull")
@click.argument("remote", required=False, metavar="REMOTE")
@click.argument("branch", required=False, metavar="BRANCH")
@click.option("--ff-only", is_flag=True, help="Require a fast-forward update (the default).")
@click.option("--rebase", is_flag=True, help="Rebase explicitly instead of fast-forward-only merge.")
@click.option("--token", default=None, help="GitHub token for this invocation.")
def pull_command(
    remote: str | None,
    branch: str | None,
    ff_only: bool,
    rebase: bool,
    token: str | None,
) -> None:
    """Pull safely from the current branch upstream or an explicit target."""

    if ff_only and rebase:
        raise click.ClickException("Use either --ff-only or --rebase, not both.")
    payload = pull(remote, branch, token, ff_only=ff_only or not rebase, rebase=rebase)
    mode = "rebased" if rebase else "fast-forwarded"
    click.echo(f"{mode.capitalize()} from {payload['remote']}/{payload['branch']}.")


@click.command(name="push")
@click.argument("remote", required=False, metavar="REMOTE")
@click.argument("refspec", required=False, metavar="REFSPEC")
@click.option("-u", "--set-upstream", is_flag=True, help="Set the branch upstream after a successful push.")
@click.option("--dry-run", is_flag=True, help="Ask Git to report the push without sending it.")
@click.option("--tags", is_flag=True, help="Push tags to the selected remote.")
@click.option("--token", default=None, help="GitHub token for this invocation.")
def push_command(
    remote: str | None,
    refspec: str | None,
    set_upstream: bool,
    dry_run: bool,
    tags: bool,
    token: str | None,
) -> None:
    """Push a validated refspec or tags without force modes."""

    payload = push(remote, refspec, token, set_upstream, dry_run, tags)
    action = "Would push" if payload["dry_run"] else "Pushed"
    target = "tags" if tags else (payload["refspec"] or "upstream")
    click.echo(f"{action} {target} to {payload['remote']}.")


@click.command(name="unset-token")
def unset_token_command() -> None:
    """Remove exactly the repository config item written by set-token."""

    click.echo(json.dumps(unset_token(), ensure_ascii=False, sort_keys=True))

"""CLI entrypoint for chatgh."""

import click
from chatstyle import add_tree_option

from chatgh import __version__
from chatgh.commands.pr import pr_group
from chatgh.github.cli import invitation_group, repo_group, repo_permissions, run_group, set_repo_token
from chatgh.github.project_cli import project_group
from chatgh.github.transport_cli import (
    fetch_command,
    pull_command,
    push_command,
    unset_token_command,
)


@click.group(name="chatgh")
@click.version_option(__version__, prog_name="chatgh")
@add_tree_option(renderer_options={"root_name": "chatgh"})
def main() -> None:
    """GitHub helpers (PR, actions, repo)."""


main.add_command(pr_group, name="pr")
main.add_command(repo_group, name="repo")
main.add_command(project_group, name="project")
main.add_command(run_group, name="run")
main.add_command(invitation_group, name="invitation")
main.add_command(repo_permissions, name="repo-perms")
main.add_command(set_repo_token, name="set-token")
main.add_command(unset_token_command, name="unset-token")
main.add_command(fetch_command, name="fetch")
main.add_command(pull_command, name="pull")
main.add_command(push_command, name="push")


if __name__ == "__main__":
    main()

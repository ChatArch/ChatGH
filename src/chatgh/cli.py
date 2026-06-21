"""CLI entrypoint for chatgh."""

import click

from chatgh.commands.pr import pr_group
from chatgh.github.cli import repo_group, repo_permissions, run_group, set_repo_token


@click.group()
def main() -> None:
    """GitHub helpers (PR, actions, repo)."""


main.add_command(pr_group, name="pr")
main.add_command(repo_group, name="repo")
main.add_command(run_group, name="run")
main.add_command(repo_permissions, name="repo-perms")
main.add_command(set_repo_token, name="set-token")


if __name__ == "__main__":
    main()

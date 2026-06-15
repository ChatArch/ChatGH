"""CLI entrypoint for chatgh."""

import click

# legacy group (original hand-written layer)
from chatgh.github.cli import cli as _legacy_cli

# new generated-layer commands (lazy-loaded internals)
from chatgh.commands.pr import pr_group as _pr_generated


@click.group()
def main() -> None:
    """GitHub helpers (PR, actions, repo)."""


# Mount legacy commands under their existing names
for cmd in _legacy_cli.commands.values():
    # legacy group has pr / run / repo-perms / set-token
    # prefix with 'legacy-' to avoid collision during transition
    if cmd.name == "pr":
        main.add_command(cmd, name="pr-legacy")
    else:
        main.add_command(cmd)

# Mount new generated-layer pr group as the default 'pr'
main.add_command(_pr_generated, name="pr")


if __name__ == "__main__":
    main()

"""CLI entrypoint for chatgh."""

import click

from chatgh import __version__
from chatgh.commands.pr import pr_group
from chatgh.github.cli import invitation_group, repo_group, repo_permissions, run_group, set_repo_token
from chatgh.github.project_cli import project_group


def _format_metavar(name: str) -> str:
    return name.replace("_", "-").upper()


def _format_argument(param: click.Argument) -> str:
    metavar = _format_metavar(param.name or "ARG")
    if not param.required:
        return f"[{metavar}]"
    if param.nargs == -1:
        return f"<{metavar}...>"
    if param.nargs and param.nargs > 1:
        return " ".join(f"<{metavar}>" for _ in range(param.nargs))
    return f"<{metavar}>"


def _option_name(param: click.Option) -> str:
    long_opts = [opt for opt in param.opts if opt.startswith("--")]
    if long_opts:
        return long_opts[0]
    return param.opts[0] if param.opts else _format_metavar(param.name or "OPTION")


def _format_option(param: click.Option) -> str:
    name = _option_name(param)
    secondary_long = next(
        (opt for opt in param.secondary_opts if opt.startswith("--")),
        None,
    )
    if param.is_bool_flag and secondary_long:
        return f"[{name}/{secondary_long}]"
    if param.is_flag:
        return f"[{name}]"
    metavar = param.metavar or _format_metavar(param.name or "VALUE")
    return f"[{name} <{metavar}>]"


def _command_signature(command: click.Command) -> str:
    parts: list[str] = []
    for param in command.params:
        if isinstance(param, click.Argument):
            parts.append(_format_argument(param))
    for param in command.params:
        if isinstance(param, click.Option):
            # The root command renders canonical pseudo-options manually so the
            # acceptance tree stays stable even if Click changes option order.
            if param.name in {"help", "version", "tree"}:
                continue
            parts.append(_format_option(param))
    return " " + " ".join(parts) if parts else ""


def _short_help(command: click.Command) -> str:
    return command.short_help or (command.help or "No description.").strip().splitlines()[0]


def render_cli_tree(root: click.Group | None = None) -> str:
    """Render the registered Click command tree for `chatgh --tree`."""
    if root is None:
        root = main
    lines = [f"chatgh  # {_short_help(root)}"]
    root_items: list[tuple[str, str | click.Command]] = [
        ("--help", "Show this help message."),
        ("--version", "Show the installed package version."),
        ("--tree", "Print the registered command tree."),
        *list(root.commands.items()),
    ]

    def walk(items: list[tuple[str, str | click.Command]], prefix: str = "") -> None:
        for index, (name, item) in enumerate(items):
            is_last = index == len(items) - 1
            connector = "└── " if is_last else "├── "
            child_prefix = prefix + ("    " if is_last else "│   ")
            if isinstance(item, str):
                lines.append(f"{prefix}{connector}{name}  # {item}")
                continue
            signature = _command_signature(item)
            lines.append(f"{prefix}{connector}{name}{signature}  # {_short_help(item)}")
            if isinstance(item, click.Group) and item.commands:
                walk(list(item.commands.items()), child_prefix)

    walk(root_items)
    return "\n".join(lines)


def _tree_callback(ctx: click.Context, _param: click.Option, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    if not isinstance(ctx.command, click.Group):
        raise click.ClickException("--tree is only available on command groups")
    click.echo(render_cli_tree(ctx.command))
    ctx.exit()


@click.group()
@click.version_option(__version__, prog_name="chatgh")
@click.option(
    "--tree",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_tree_callback,
    help="Print the registered command tree.",
)
def main() -> None:
    """GitHub helpers (PR, actions, repo)."""


main.add_command(pr_group, name="pr")
main.add_command(repo_group, name="repo")
main.add_command(project_group, name="project")
main.add_command(run_group, name="run")
main.add_command(invitation_group, name="invitation")
main.add_command(repo_permissions, name="repo-perms")
main.add_command(set_repo_token, name="set-token")


if __name__ == "__main__":
    main()

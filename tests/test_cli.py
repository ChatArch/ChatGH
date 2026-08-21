from click.testing import CliRunner

from chatgh.cli import main


def test_chatgh_help_lists_tree_options_and_github_commands():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    for option in ("--tree", "--tree-brief"):
        assert option in result.output
    for command in (
        "pr",
        "repo",
        "project",
        "run",
        "invitation",
        "repo-perms",
        "set-token",
    ):
        assert command in result.output


def test_chatgh_tree_option_renders_registered_command_surface():
    result = CliRunner().invoke(main, ["--tree"])

    assert result.exit_code == 0, result.output
    assert result.output.startswith("chatgh\n")
    for option in ("--help", "--version", "--tree", "--tree-brief"):
        assert option in result.output
    assert "├── pr" in result.output
    assert "│   ├── checks [NUMBER]" in result.output
    assert "├── repo" in result.output
    assert "│   └── transfer" in result.output
    assert "├── project" in result.output
    assert "│   ├── item" in result.output
    assert "│   │   ├── edit" in result.output
    assert "│   ├── field" in result.output
    assert "│   │   ├── list" in result.output
    assert "├── run" in result.output
    assert "│   └── logs" in result.output
    assert "├── invitation" in result.output
    assert "│   ├── accept" in result.output
    assert "├── repo-perms" in result.output
    assert "└── set-token" in result.output
    assert "clone <REPO> [DIRECTORY]" in result.output
    assert "hello" not in result.output.lower()


def test_chatgh_tree_brief_omits_parameter_signatures():
    result = CliRunner().invoke(main, ["--tree-brief"])

    assert result.exit_code == 0, result.output
    assert result.output.startswith("chatgh\n")
    assert "clone  # Clone a repository without overwriting an existing directory." in result.output
    assert "checks  # Show CI check status for a pull request." in result.output
    assert "<REPO>" not in result.output
    assert "[DIRECTORY]" not in result.output
    assert "[NUMBER]" not in result.output


def test_chatgh_version_option():
    result = CliRunner().invoke(main, ["--version"])

    assert result.exit_code == 0
    assert "0.2.12" in result.output

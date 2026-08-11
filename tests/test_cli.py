from click.testing import CliRunner

from chatgh.cli import main


def test_chatgh_help_lists_github_commands():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "pr" in result.output
    assert "repo" in result.output
    assert "project" in result.output
    assert "run" in result.output
    assert "repo-perms" in result.output
    assert "set-token" in result.output


def test_chatgh_help_lists_tree_option():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "--tree" in result.output


def test_chatgh_tree_option_renders_registered_command_surface():
    result = CliRunner().invoke(main, ["--tree"])

    assert result.exit_code == 0
    assert "chatgh  # GitHub helpers" in result.output
    assert "├── --help" in result.output
    assert "├── --version" in result.output
    assert "├── --tree" in result.output
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
    assert "hello" not in result.output.lower()


def test_chatgh_version_option():
    result = CliRunner().invoke(main, ["--version"])

    assert result.exit_code == 0
    assert "0.2.11" in result.output

from click.testing import CliRunner

from chatgh.cli import main


def test_chatgh_help_lists_github_commands():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "pr" in result.output
    assert "run" in result.output
    assert "repo-perms" in result.output
    assert "set-token" in result.output


def test_chatgh_version_option():
    result = CliRunner().invoke(main, ["--version"])

    assert result.exit_code == 0
    assert "0.2.8" in result.output

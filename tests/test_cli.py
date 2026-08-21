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
    for group in ("├── pr", "├── repo", "├── project", "├── run", "├── invitation"):
        assert group in result.output
    for signature in (
        "checks [NUMBER]",
        "clone <REPO> [DIRECTORY]",
        "transfer [REPO-ARG]",
        "edit [NUMBER] [--owner OWNER] [--id ITEM-ID]",
        "list [NUMBER] [--owner OWNER] [--limit LIMIT]",
        "logs [--repo REPO] [--job-id JOB-ID]",
        "accept <INVITATION-ID>",
        "repo-perms [--repo REPO]",
        "set-token [--token TOKEN]",
    ):
        assert signature in result.output
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

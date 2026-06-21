import pytest
from click.testing import CliRunner

from chatgh.cli import main as cli


pytestmark = pytest.mark.mock_cli


@pytest.fixture
def runner():
    return CliRunner()


def test_chatgh_help_commands(runner):
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "pr" in result.output
    assert "pr-legacy" not in result.output


def test_chatgh_pr_help_commands(runner):
    result = runner.invoke(cli, ["pr", "--help"])

    assert result.exit_code == 0
    for command in ["list", "view", "checks"]:
        assert command in result.output
    for removed in ["create", "comment", "merge", "edit"]:
        assert removed not in result.output


def test_chatgh_pr_view_uses_positional_number(runner):
    result = runner.invoke(cli, ["pr", "view", "--help"])

    assert result.exit_code == 0
    assert "[NUMBER]" in result.output
    assert "--number" not in result.output


def test_chatgh_pr_checks_uses_positional_number(runner):
    result = runner.invoke(cli, ["pr", "checks", "--help"])

    assert result.exit_code == 0
    assert "[NUMBER]" in result.output
    assert "--number" not in result.output


def test_chatgh_pr_list_renders_json(monkeypatch, runner):
    monkeypatch.setattr(
        "chatgh.github.commands.list_prs",
        lambda repo, state, limit, token: [
            {"number": 138, "state": "open", "title": "Move GitHub helpers"}
        ],
    )

    result = runner.invoke(
        cli, ["pr", "list", "--repo", "owner/repo", "--json-output"]
    )

    assert result.exit_code == 0
    assert '"number": 138' in result.output


def test_chatgh_pr_view_renders_summary(monkeypatch, runner):
    monkeypatch.setattr(
        "chatgh.github.commands.view_pr",
        lambda repo, number, token: {
            "number": number,
            "title": "Move GitHub helpers",
            "state": "open",
            "url": "https://github.com/owner/repo/pull/138",
            "author": "rex",
            "created_at": None,
            "updated_at": None,
            "merged_at": None,
            "base": "main",
            "head": "rex/chatgh",
            "mergeable": True,
            "mergeable_state": "clean",
        },
    )

    result = runner.invoke(cli, ["pr", "view", "138", "--repo", "owner/repo"])

    assert result.exit_code == 0
    assert "#138 [open] Move GitHub helpers" in result.output


def test_chatgh_pr_checks_renders_json(monkeypatch, runner):
    monkeypatch.setattr(
        "chatgh.github.commands.check_pr",
        lambda *args, **kwargs: {
            "number": 138,
            "title": "Move GitHub helpers",
            "state": "open",
            "url": "https://github.com/owner/repo/pull/138",
            "author": "rex",
            "base": "main",
            "head": "rex/chatgh",
            "head_sha": "abc123",
            "mergeable": True,
            "mergeable_state": "clean",
            "combined_status": {"state": "success", "total_count": 0, "statuses": []},
            "check_runs": [],
            "check_runs_error": None,
            "workflow_runs": [],
            "workflow_runs_error": None,
        },
    )

    result = runner.invoke(
        cli, ["pr", "checks", "138", "--repo", "owner/repo", "--json-output"]
    )

    assert result.exit_code == 0
    assert '"mergeable_state": "clean"' in result.output

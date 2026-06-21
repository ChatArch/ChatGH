import pytest
from click.testing import CliRunner

from chatgh.cli import main as cli
from chatgh.github.requests import _build_repo_payload, _parse_time


pytestmark = pytest.mark.mock_cli


@pytest.fixture
def runner():
    return CliRunner()


def test_chatgh_help_commands(runner):
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "pr" in result.output
    assert "repo" in result.output
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


def test_chatgh_repo_help_commands(runner):
    result = runner.invoke(cli, ["repo", "--help"])

    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output


def test_chatgh_repo_list_renders_json(monkeypatch, runner):
    captured = {}

    def fake_list(owner, limit, sort, direction, token):
        captured.update({"owner": owner, "limit": limit, "sort": sort, "direction": direction})
        return [
            {
                "full_name": f"{owner}/ChatBlog",
                "visibility": "private",
                "private": True,
                "stars": 7,
                "open_prs": 2,
                "open_issues": 3,
                "updated_at": "2026-06-21T10:00:00+00:00",
                "created_at": "2026-06-01T10:00:00+00:00",
                "html_url": "https://github.com/ChatArch/ChatBlog",
            }
        ]

    monkeypatch.setattr(
        "chatgh.github.cli.list_repos",
        fake_list,
    )

    result = runner.invoke(
        cli,
        [
            "repo",
            "list",
            "--owner",
            "ChatArch",
            "--limit",
            "5",
            "--sort",
            "created",
            "--direction",
            "asc",
            "--json-output",
        ],
    )

    assert result.exit_code == 0
    assert '"full_name": "ChatArch/ChatBlog"' in result.output
    assert '"open_prs": 2' in result.output
    assert captured == {
        "owner": "ChatArch",
        "limit": 5,
        "sort": "created",
        "direction": "asc",
    }


def test_chatgh_repo_list_renders_table(monkeypatch, runner):
    monkeypatch.setattr(
        "chatgh.github.cli.list_repos",
        lambda owner, limit, sort, direction, token: [
            {
                "full_name": f"{owner}/ChatBlog",
                "visibility": "private",
                "stars": 7,
                "open_prs": 2,
                "open_issues": 3,
                "updated_at": "2026-06-21T10:00:00+00:00",
                "created_at": "2026-06-01T10:00:00+00:00",
            }
        ],
    )

    result = runner.invoke(cli, ["repo", "list", "--owner", "ChatArch"])

    assert result.exit_code == 0
    assert "repo" in result.output
    assert "vis" in result.output
    assert "stars" in result.output
    assert "prs" in result.output
    assert "issues" in result.output
    assert "ChatArch/ChatBlog" in result.output
    assert "private" in result.output


def test_chatgh_repo_create_defaults_private(monkeypatch, runner):
    captured = {}

    def fake_create(owner, name, private, description, if_exists, token):
        captured.update({"owner": owner, "name": name, "private": private, "if_exists": if_exists})
        return {
            "full_name": f"{owner}/{name}",
            "private": private,
            "created": True,
            "html_url": f"https://github.com/{owner}/{name}",
        }

    monkeypatch.setattr("chatgh.github.cli.create_repo", fake_create)

    result = runner.invoke(
        cli,
        ["repo", "create", "--owner", "ChatArch", "--name", "hermes-agent"],
    )

    assert result.exit_code == 0
    assert "created: ChatArch/hermes-agent (private)" in result.output
    assert captured == {
        "owner": "ChatArch",
        "name": "hermes-agent",
        "private": True,
        "if_exists": "error",
    }


def test_repo_sort_time_handles_naive_and_missing_values():
    assert _parse_time("2026-06-21T10:00:00").tzinfo is not None
    assert _parse_time(None).tzinfo is not None


def test_repo_payload_does_not_invent_open_issues_when_pr_count_fails():
    class _Repo:
        name = "demo"
        full_name = "ChatArch/demo"
        private = True
        visibility = "private"
        stargazers_count = 0
        forks_count = 0
        open_issues_count = 5
        archived = False
        fork = False
        created_at = None
        updated_at = None
        pushed_at = None
        html_url = "https://github.com/ChatArch/demo"
        clone_url = "https://github.com/ChatArch/demo.git"
        ssh_url = "git@github.com:ChatArch/demo.git"
        default_branch = "main"
        description = None

        def get_pulls(self, state):
            raise RuntimeError("rate limited")

    payload = _build_repo_payload(_Repo())

    assert payload["open_prs"] is None
    assert payload["open_issues"] is None
    assert payload["open_issues_reported"] == 5

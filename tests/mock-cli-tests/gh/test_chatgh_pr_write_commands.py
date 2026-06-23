import pytest
from click.testing import CliRunner

from chatgh.cli import main as cli


pytestmark = pytest.mark.mock_cli


@pytest.fixture
def runner():
    return CliRunner()


def _pr_payload(number=139, title="Add feature", state="open", base="main", head="rex/feature"):
    return {
        "number": number,
        "title": title,
        "state": state,
        "url": f"https://github.com/owner/repo/pull/{number}",
        "author": "rex",
        "base": base,
        "head": head,
        "head_sha": "abc123",
        "created_at": None,
        "updated_at": None,
        "merged_at": None,
        "mergeable": None,
        "mergeable_state": None,
    }


def test_chatgh_pr_create_renders_json(monkeypatch, runner, tmp_path):
    body_file = tmp_path / "body.md"
    body_file.write_text("PR body\n", encoding="utf-8")
    captured = {}

    def fake_create(repo, base, head, title, body, token):
        captured.update(
            {"repo": repo, "base": base, "head": head, "title": title, "body": body}
        )
        return _pr_payload(number=139, title=title, base=base, head=head)

    monkeypatch.setattr("chatgh.github.commands.create_pr", fake_create)

    result = runner.invoke(
        cli,
        [
            "pr",
            "create",
            "--repo",
            "owner/repo",
            "--base",
            "main",
            "--head",
            "rex/feature",
            "--title",
            "Add feature",
            "--body-file",
            str(body_file),
            "--json-output",
        ],
    )

    assert result.exit_code == 0
    assert '"number": 139' in result.output
    assert captured == {
        "repo": "owner/repo",
        "base": "main",
        "head": "rex/feature",
        "title": "Add feature",
        "body": "PR body\n",
    }


def test_chatgh_pr_create_no_interactive_fails_for_missing_required(runner):
    result = runner.invoke(cli, ["pr", "create", "-I"])

    assert result.exit_code != 0
    assert "Missing required value: base" in result.output


def test_chatgh_pr_comment_renders_json(monkeypatch, runner):
    captured = {}

    def fake_comment(repo, number, body, token):
        captured.update({"repo": repo, "number": number, "body": body})
        return {
            "url": "https://github.com/owner/repo/pull/138#issuecomment-1",
            "id": 1,
            "body": body,
        }

    monkeypatch.setattr("chatgh.github.commands.comment_pr", fake_comment)

    result = runner.invoke(
        cli,
        [
            "pr",
            "comment",
            "138",
            "--repo",
            "owner/repo",
            "--body",
            "Looks good",
            "--json-output",
        ],
    )

    assert result.exit_code == 0
    assert '"id": 1' in result.output
    assert captured == {"repo": "owner/repo", "number": 138, "body": "Looks good"}


def test_chatgh_pr_edit_passes_updates(monkeypatch, runner):
    captured = {}

    def fake_edit(repo, number, title, body, state, base, token):
        captured.update(
            {
                "repo": repo,
                "number": number,
                "title": title,
                "body": body,
                "state": state,
                "base": base,
            }
        )
        return _pr_payload(number=number, title=title, state=state, base=base)

    monkeypatch.setattr("chatgh.github.commands.edit_pr", fake_edit)

    result = runner.invoke(
        cli,
        [
            "pr",
            "edit",
            "138",
            "--repo",
            "owner/repo",
            "--title",
            "New title",
            "--body",
            "New body",
            "--state",
            "open",
            "--base",
            "main",
        ],
    )

    assert result.exit_code == 0
    assert "#138 [open] New title" in result.output
    assert captured == {
        "repo": "owner/repo",
        "number": 138,
        "title": "New title",
        "body": "New body",
        "state": "open",
        "base": "main",
    }


def test_chatgh_pr_merge_defaults_to_squash_with_check(monkeypatch, runner):
    captured = {}

    def fake_merge(repo, number, method, title, message, check_before_merge, token):
        captured.update(
            {
                "repo": repo,
                "number": number,
                "method": method,
                "title": title,
                "message": message,
                "check_before_merge": check_before_merge,
            }
        )
        return {
            "merged": True,
            "message": "merged",
            "url": "https://github.com/owner/repo/pull/138",
        }

    monkeypatch.setattr("chatgh.github.commands.merge_pr", fake_merge)

    result = runner.invoke(
        cli,
        [
            "pr",
            "merge",
            "138",
            "--repo",
            "owner/repo",
            "--title",
            "Merge title",
            "--message",
            "Merge message",
        ],
    )

    assert result.exit_code == 0
    assert "Merged: https://github.com/owner/repo/pull/138" in result.output
    assert captured == {
        "repo": "owner/repo",
        "number": 138,
        "method": "squash",
        "title": "Merge title",
        "message": "Merge message",
        "check_before_merge": True,
    }

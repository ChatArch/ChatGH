import json

import pytest
from click.testing import CliRunner

from chatgh.cli import main as cli


pytestmark = pytest.mark.mock_cli


@pytest.fixture
def runner():
    return CliRunner()


def test_repo_common_commands_are_registered(runner):
    result = runner.invoke(cli, ["repo", "--help"])

    assert result.exit_code == 0
    for command in ["view", "clone", "sync", "edit"]:
        assert command in result.output


def test_pr_common_commands_are_registered(runner):
    result = runner.invoke(cli, ["pr", "--help"])

    assert result.exit_code == 0
    for command in ["status", "diff", "close", "reopen", "review", "ready", "update-branch"]:
        assert command in result.output


def test_run_common_commands_are_registered(runner):
    result = runner.invoke(cli, ["run", "--help"])

    assert result.exit_code == 0
    for command in ["list", "watch", "rerun", "cancel", "download"]:
        assert command in result.output


def test_repo_view_accepts_positional_repo_and_json(monkeypatch, runner):
    captured = {}

    def fake_view(repo, token):
        captured.update({"repo": repo, "token": token})
        return {"full_name": repo, "default_branch": "main"}

    monkeypatch.setattr("chatgh.github.cli.view_repo", fake_view)

    result = runner.invoke(cli, ["repo", "view", "owner/repo", "--json-output"])

    assert result.exit_code == 0
    assert captured == {"repo": "owner/repo", "token": None}
    assert '"full_name": "owner/repo"' in result.output


def test_repo_edit_visibility_requires_consequence_acknowledgement(runner):
    result = runner.invoke(
        cli,
        [
            "repo",
            "edit",
            "owner/repo",
            "--visibility",
            "public",
            "--json-output",
        ],
    )

    assert result.exit_code != 0
    assert "--accept-visibility-change-consequences" in result.output


def test_repo_edit_maps_visibility_and_description(monkeypatch, runner):
    captured = {}

    def fake_edit(repo, description, homepage, default_branch, visibility, accept_visibility_change_consequences, token):
        captured.update(
            {
                "repo": repo,
                "description": description,
                "homepage": homepage,
                "default_branch": default_branch,
                "visibility": visibility,
                "accept_visibility_change_consequences": accept_visibility_change_consequences,
                "token": token,
            }
        )
        return {"full_name": repo, "description": description, "visibility": visibility}

    monkeypatch.setattr("chatgh.github.cli.edit_repo", fake_edit)

    result = runner.invoke(
        cli,
        [
            "repo",
            "edit",
            "owner/repo",
            "--description",
            "demo",
            "--visibility",
            "private",
            "--accept-visibility-change-consequences",
            "--json-output",
        ],
    )

    assert result.exit_code == 0
    assert captured["repo"] == "owner/repo"
    assert captured["description"] == "demo"
    assert captured["visibility"] == "private"
    assert captured["accept_visibility_change_consequences"] is True


def test_pr_close_and_reopen_dispatch_to_python_api(monkeypatch, runner):
    calls = []

    def fake_close(repo, number, comment, delete_branch, token):
        calls.append(("close", repo, number, comment, delete_branch, token))
        return {"number": number, "state": "closed"}

    def fake_reopen(repo, number, token):
        calls.append(("reopen", repo, number, token))
        return {"number": number, "state": "open"}

    monkeypatch.setattr("chatgh.commands.pr.close_pr", fake_close)
    monkeypatch.setattr("chatgh.commands.pr.reopen_pr", fake_reopen)

    close_result = runner.invoke(cli, ["pr", "close", "7", "--repo", "owner/repo", "--comment", "done", "--delete-branch", "--json-output"])
    reopen_result = runner.invoke(cli, ["pr", "reopen", "7", "--repo", "owner/repo", "--json-output"])

    assert close_result.exit_code == 0
    assert reopen_result.exit_code == 0
    assert calls == [
        ("close", "owner/repo", 7, "done", True, None),
        ("reopen", "owner/repo", 7, None),
    ]


def test_pr_review_approves_with_body_file(monkeypatch, runner, tmp_path):
    body_file = tmp_path / "review.md"
    body_file.write_text("looks good", encoding="utf-8")
    captured = {}

    def fake_review(repo, number, event, body, token):
        captured.update({"repo": repo, "number": number, "event": event, "body": body, "token": token})
        return {"number": number, "event": event, "body": body}

    monkeypatch.setattr("chatgh.commands.pr.review_pr", fake_review)

    result = runner.invoke(
        cli,
        ["pr", "review", "12", "--repo", "owner/repo", "--approve", "--body-file", str(body_file), "--json-output"],
    )

    assert result.exit_code == 0
    assert captured == {"repo": "owner/repo", "number": 12, "event": "APPROVE", "body": "looks good", "token": None}


def test_pr_ready_dispatches_to_python_api(monkeypatch, runner):
    captured = {}

    def fake_ready(repo, number, token):
        captured.update({"repo": repo, "number": number, "token": token})
        return {"number": number, "ready": True}

    monkeypatch.setattr("chatgh.commands.pr.ready_pr", fake_ready)

    result = runner.invoke(cli, ["pr", "ready", "15", "--repo", "owner/repo", "--json-output"])

    assert result.exit_code == 0
    assert captured == {"repo": "owner/repo", "number": 15, "token": None}
    assert '"ready": true' in result.output


def test_pr_diff_outputs_patch_text(monkeypatch, runner):
    monkeypatch.setattr("chatgh.commands.pr.diff_pr", lambda repo, number, token: "diff --git a/x b/x\n")

    result = runner.invoke(cli, ["pr", "diff", "3", "--repo", "owner/repo"])

    assert result.exit_code == 0
    assert "diff --git" in result.output


def test_run_list_and_cancel_dispatch(monkeypatch, runner):
    captured = {}

    def fake_list(repo, branch, status, event, limit, token):
        captured.update({"repo": repo, "branch": branch, "status": status, "event": event, "limit": limit, "token": token})
        return [{"id": 42, "status": "completed"}]

    def fake_cancel(repo, run_id, token):
        captured.update({"cancel_repo": repo, "run_id": run_id, "cancel_token": token})
        return {"id": run_id, "cancelled": True}

    monkeypatch.setattr("chatgh.github.cli.list_runs", fake_list)
    monkeypatch.setattr("chatgh.github.cli.cancel_run", fake_cancel)

    list_result = runner.invoke(cli, ["run", "list", "--repo", "owner/repo", "--branch", "main", "--status", "completed", "--limit", "5", "--json-output"])
    cancel_result = runner.invoke(cli, ["run", "cancel", "42", "--repo", "owner/repo", "--json-output"])

    assert list_result.exit_code == 0
    assert cancel_result.exit_code == 0
    assert captured["repo"] == "owner/repo"
    assert captured["branch"] == "main"
    assert captured["status"] == "completed"
    assert captured["limit"] == 5
    assert captured["cancel_repo"] == "owner/repo"
    assert captured["run_id"] == 42


def test_run_download_dispatches_output_dir(monkeypatch, runner, tmp_path):
    captured = {}

    def fake_download(repo, run_id, name, output_dir, token):
        captured.update({"repo": repo, "run_id": run_id, "name": name, "output_dir": output_dir, "token": token})
        return {"id": run_id, "output_dir": output_dir, "files": []}

    monkeypatch.setattr("chatgh.github.cli.download_run_artifacts", fake_download)

    result = runner.invoke(cli, ["run", "download", "9", "--repo", "owner/repo", "--name", "dist", "--dir", str(tmp_path), "--json-output"])

    assert result.exit_code == 0
    assert captured["repo"] == "owner/repo"
    assert captured["run_id"] == 9
    assert captured["name"] == "dist"
    assert captured["output_dir"] == str(tmp_path)


def test_post_pr_ready_uses_graphql_mutation(monkeypatch):
    from chatgh.github import requests as gh_requests

    captured = {}

    def fake_get_json(repo, path, token):
        captured.update({"repo": repo, "path": path, "token": token})
        return {"node_id": "PR_node_123"}

    class FakeResponse:
        ok = True
        status_code = 200
        text = "{}"

        def json(self):
            return {"data": {"markPullRequestReadyForReview": {"pullRequest": {"number": 15}}}}

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(gh_requests, "github_api_get_json", fake_get_json)
    monkeypatch.setattr("requests.post", fake_post)

    payload = gh_requests.post_pr_ready("owner/repo", 15, "token")

    assert payload == {"number": 15, "ready": True}
    assert captured["path"] == "/pulls/15"
    assert captured["url"] == "https://api.github.com/graphql"
    assert "markPullRequestReadyForReview" in captured["json"]["query"]
    assert captured["json"]["variables"] == {"pullRequestId": "PR_node_123"}


def test_sync_repo_refuses_mismatched_checkout(monkeypatch):
    import click
    from chatgh.github import commands

    monkeypatch.setattr(commands, "resolve_repo_from_git_remote", lambda: ("owner/current", {"path": "owner/current"}))

    with pytest.raises(click.ClickException, match="current checkout is owner/current"):
        commands.sync_repo("owner/other", branch="main", remote="origin", ff_only=True, token=None)


def test_download_run_artifact_sanitizes_artifact_name(monkeypatch, tmp_path):
    import io
    import zipfile
    from chatgh.github import requests as gh_requests

    def fake_get_json(repo, path, token):
        assert path == "/actions/runs/9/artifacts"
        return {"artifacts": [{"id": 123, "name": "../dist", "size_in_bytes": 10}]}

    class FakeResponse:
        ok = True
        status_code = 200
        text = ""

        def __init__(self):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr("result.txt", "ok")
            self.content = buffer.getvalue()

    monkeypatch.setattr(gh_requests, "github_api_get_json", fake_get_json)
    monkeypatch.setattr("requests.get", lambda *args, **kwargs: FakeResponse())

    payload = gh_requests.download_run_artifact_zip("owner/repo", 9, "token", name=None, output_dir=str(tmp_path))

    assert payload["files"][0]["name"] == "dist"
    assert (tmp_path / "dist.zip").is_file()
    assert (tmp_path / "dist" / "result.txt").read_text(encoding="utf-8") == "ok"


def test_download_run_artifact_rejects_zip_path_traversal(monkeypatch, tmp_path):
    import click
    import io
    import zipfile
    from chatgh.github import requests as gh_requests

    def fake_get_json(repo, path, token):
        return {"artifacts": [{"id": 123, "name": "artifact", "size_in_bytes": 10}]}

    class FakeResponse:
        ok = True
        status_code = 200
        text = ""

        def __init__(self):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr("../pwn.txt", "bad")
            self.content = buffer.getvalue()

    monkeypatch.setattr(gh_requests, "github_api_get_json", fake_get_json)
    monkeypatch.setattr("requests.get", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(click.ClickException, match="unsafe artifact path"):
        gh_requests.download_run_artifact_zip("owner/repo", 9, "token", name=None, output_dir=str(tmp_path))

    assert not (tmp_path / "pwn.txt").exists()

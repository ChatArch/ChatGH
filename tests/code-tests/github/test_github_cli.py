from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from chatgh.github.client import GitHubClient
import chatgh.github.commands as gh_commands


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _fake_pr_checks_payload():
    return {
        "number": 138,
        "title": "Improve setup and CI visibility",
        "state": "open",
        "url": "https://github.com/CubeNLP/ChatTool/pull/138",
        "author": "rex",
        "base": "vibe/master",
        "head": "rex/setup",
        "head_sha": "abc123def456",
        "mergeable": False,
        "mergeable_state": "dirty",
        "combined_status": {
            "state": "pending",
            "sha": "abc123def456",
            "total_count": 2,
            "statuses": [
                {
                    "context": "ci/test",
                    "state": "success",
                    "description": "pytest passed",
                    "target_url": "https://ci.example.com/test",
                    "updated_at": _dt("2026-03-23T10:00:00Z").isoformat(),
                },
                {
                    "context": "ci/lint",
                    "state": "pending",
                    "description": "ruff running",
                    "target_url": "https://ci.example.com/lint",
                    "updated_at": _dt("2026-03-23T10:05:00Z").isoformat(),
                },
            ],
        },
        "check_runs": [
            {
                "name": "tests",
                "status": "completed",
                "conclusion": "success",
                "details_url": "https://github.com/CubeNLP/ChatTool/actions/runs/1/job/11",
                "html_url": "https://github.com/CubeNLP/ChatTool/runs/11",
                "app": "GitHub Actions",
                "started_at": _dt("2026-03-23T09:55:00Z").isoformat(),
                "completed_at": _dt("2026-03-23T10:00:00Z").isoformat(),
            },
            {
                "name": "lint",
                "status": "in_progress",
                "conclusion": None,
                "details_url": "https://github.com/CubeNLP/ChatTool/actions/runs/1/job/12",
                "html_url": "https://github.com/CubeNLP/ChatTool/runs/12",
                "app": "GitHub Actions",
                "started_at": _dt("2026-03-23T10:01:00Z").isoformat(),
                "completed_at": None,
            },
        ],
        "check_runs_error": None,
        "workflow_runs": [
            {
                "name": "CI",
                "display_title": "CI / tests",
                "event": "pull_request",
                "status": "in_progress",
                "conclusion": None,
                "html_url": "https://github.com/CubeNLP/ChatTool/actions/runs/1",
                "created_at": _dt("2026-03-23T09:50:00Z").isoformat(),
                "updated_at": _dt("2026-03-23T10:05:00Z").isoformat(),
                "run_started_at": _dt("2026-03-23T09:51:00Z").isoformat(),
                "head_branch": "rex/setup",
                "head_sha": "abc123def456",
                "run_number": 501,
            }
        ],
        "workflow_runs_error": None,
    }


def _fake_run_view_payload():
    return {
        "id": 23494900414,
        "name": "Python Package",
        "display_title": "Python Package / pull_request",
        "event": "pull_request",
        "status": "completed",
        "conclusion": "failure",
        "html_url": "https://github.com/CubeNLP/ChatTool/actions/runs/23494900414",
        "created_at": "2026-03-24T01:15:00Z",
        "updated_at": "2026-03-24T01:18:00Z",
        "run_started_at": "2026-03-24T01:15:30Z",
        "head_branch": "rex/fix-ci-after-feishu",
        "head_sha": "b4a242b43599a6d0015442c63b2836de211b6273",
        "run_number": 151,
        "jobs_total_count": 1,
        "jobs": [
            {
                "id": 68373094563,
                "name": "build (3.10, ubuntu-latest)",
                "status": "completed",
                "conclusion": "failure",
                "html_url": "https://github.com/CubeNLP/ChatTool/actions/runs/23494900414/job/68373094563",
                "runner_name": "GitHub Actions 7",
                "runner_group_name": "GitHub Actions",
                "labels": ["ubuntu-latest"],
                "started_at": "2026-03-24T01:15:40Z",
                "completed_at": "2026-03-24T01:17:00Z",
                "steps": [
                    {
                        "number": 8,
                        "name": "Test CLI docs and real flows",
                        "status": "completed",
                        "conclusion": "success",
                    },
                    {
                        "number": 9,
                        "name": "Check test results",
                        "status": "completed",
                        "conclusion": "failure",
                    },
                ],
            }
        ],
    }


def test_merge_pr_blocks_failed_ci(monkeypatch):
    merge_calls = []
    monkeypatch.setattr(gh_commands, "resolve_repo_and_credential_path", lambda repo: ("CubeNLP/ChatTool", "CubeNLP/ChatTool.git"))
    monkeypatch.setattr(
        gh_commands,
        "get_client",
        lambda token, require_token=False, credential_path=None: object(),
    )
    monkeypatch.setattr(
        gh_commands,
        "get_pr_checks",
        lambda *args, **kwargs: {
            **_fake_pr_checks_payload(),
            "check_runs": [{"name": "build", "status": "completed", "conclusion": "failure"}],
            "workflow_runs": [{"name": "CI", "status": "completed", "conclusion": "failure"}],
        },
    )
    monkeypatch.setattr(
        gh_commands,
        "post_pr_merge",
        lambda *args, **kwargs: merge_calls.append(True),
    )

    with pytest.raises(Exception) as excinfo:
        gh_commands.merge_pr(None, 138, "merge", None, None, True, None)

    assert "Refusing to merge because CI checks are not green" in str(excinfo.value)
    assert not merge_calls


def test_merge_pr_without_check_keeps_current_behavior(monkeypatch):
    monkeypatch.setattr(gh_commands, "resolve_repo_and_credential_path", lambda repo: ("CubeNLP/ChatTool", "CubeNLP/ChatTool.git"))
    monkeypatch.setattr(
        gh_commands,
        "get_client",
        lambda token, require_token=False, credential_path=None: object(),
    )
    monkeypatch.setattr(
        gh_commands,
        "post_pr_merge",
        lambda *args, **kwargs: {"merged": True, "message": "merged", "url": "https://github.com/CubeNLP/ChatTool/pull/138"},
    )

    result = gh_commands.merge_pr(None, 138, "merge", None, None, False, None)

    assert result["merged"] is True
    assert result["url"].endswith("/138")


def test_check_pr_wait_loops_until_complete(monkeypatch):
    payloads = iter(
        [
            {
                **_fake_pr_checks_payload(),
                "check_runs": [{"name": "tests", "status": "in_progress", "conclusion": None}],
                "workflow_runs": [],
            },
            {
                **_fake_pr_checks_payload(),
                "combined_status": {"state": "success", "sha": "abc123def456", "total_count": 0, "statuses": []},
                "check_runs": [{"name": "tests", "status": "completed", "conclusion": "success"}],
                "workflow_runs": [],
            },
        ]
    )
    monkeypatch.setattr(gh_commands, "resolve_repo_and_credential_path", lambda repo: ("CubeNLP/ChatTool", "CubeNLP/ChatTool.git"))
    monkeypatch.setattr(
        gh_commands,
        "get_client",
        lambda token, require_token=False, credential_path=None: object(),
    )
    monkeypatch.setattr(gh_commands, "get_pr_checks", lambda *args, **kwargs: next(payloads))
    sleeps = []
    monkeypatch.setattr(gh_commands.time, "sleep", lambda seconds: sleeps.append(seconds))

    payload = gh_commands.check_pr(None, 138, 20, 10, True, 0.01, 1, None)

    assert payload["check_runs"][0]["status"] == "completed"
    assert sleeps == [0.01]


def test_github_client_thin_wrapper_calls_extracted_request(monkeypatch):
    fake_repo = SimpleNamespace(get_pull=lambda number: SimpleNamespace(
        number=number,
        title="Test PR",
        state="open",
        html_url="https://github.com/CubeNLP/ChatTool/pull/138",
        user=SimpleNamespace(login="rex"),
        base=SimpleNamespace(ref="main"),
        head=SimpleNamespace(ref="rex/test", sha="abc123"),
        created_at=None,
        updated_at=None,
        merged_at=None,
        mergeable=True,
        mergeable_state="clean",
    ))
    monkeypatch.setattr(
        "chatgh.github.client.get_client",
        lambda token, require_token=False, credential_path=None: SimpleNamespace(get_repo=lambda repo: fake_repo),
    )

    client = GitHubClient(user_name="octocat", token="ghp_test")
    payload = client.get_pr_view("CubeNLP/ChatTool", 138)

    assert payload["number"] == 138
    assert payload["mergeable_state"] == "clean"

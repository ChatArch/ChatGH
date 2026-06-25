import pytest
from click.testing import CliRunner

from chatgh.cli import main as cli
from chatgh.github.requests import _build_repo_payload, _parse_time, post_repo_fork


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
    for command in ["list", "create", "view", "comment", "edit", "checks", "merge"]:
        assert command in result.output


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


def test_chatgh_repo_list_prompts_for_missing_owner(monkeypatch, runner):
    captured = {}

    monkeypatch.setattr("chatgh.github.cli.is_interactive_available", lambda: True)
    monkeypatch.setattr("chatgh.github.cli.ask_text", lambda prompt, **kwargs: "ChatArch")

    def fake_list(owner, limit, sort, direction, token):
        captured.update({"owner": owner, "limit": limit, "sort": sort, "direction": direction})
        return []

    monkeypatch.setattr("chatgh.github.cli.list_repos", fake_list)

    result = runner.invoke(cli, ["repo", "list"])

    assert result.exit_code == 0
    assert captured["owner"] == "ChatArch"


def test_chatgh_repo_list_no_interactive_fails_for_missing_owner(runner):
    result = runner.invoke(cli, ["repo", "list", "-I"])

    assert result.exit_code != 0
    assert "Missing required value: owner" in result.output


def test_chatgh_repo_create_prompts_for_missing_owner_and_name(monkeypatch, runner):
    prompts = iter(["ChatArch", "ChatDemo"])
    captured = {}

    monkeypatch.setattr("chatgh.github.cli.is_interactive_available", lambda: True)
    monkeypatch.setattr("chatgh.github.cli.ask_text", lambda prompt, **kwargs: next(prompts))

    def fake_create(owner, name, private, description, if_exists, token):
        captured.update({"owner": owner, "name": name, "private": private, "if_exists": if_exists})
        return {"full_name": f"{owner}/{name}", "private": private, "created": True}

    monkeypatch.setattr("chatgh.github.cli.create_repo", fake_create)

    result = runner.invoke(cli, ["repo", "create"])

    assert result.exit_code == 0
    assert "created: ChatArch/ChatDemo (private)" in result.output
    assert captured == {
        "owner": "ChatArch",
        "name": "ChatDemo",
        "private": True,
        "if_exists": "error",
    }


def test_chatgh_repo_create_no_interactive_fails_for_missing_owner_and_name(runner):
    result = runner.invoke(cli, ["repo", "create", "-I"])

    assert result.exit_code != 0
    assert "Missing required value: owner" in result.output


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
                "default_branch": "main",
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


def test_chatgh_repo_protection_renders_single_repo_summary(monkeypatch, runner):
    monkeypatch.setattr(
        "chatgh.github.cli.inspect_repo_protection",
        lambda repo, token: {
            "repo": repo,
            "default_branch": "master",
            "default_branch_protected": True,
            "branch_protection": {
                "enabled": True,
                "required_pull_request_reviews": True,
                "required_approving_review_count": 0,
                "allow_force_pushes": False,
                "allow_deletions": False,
            },
            "rulesets": [],
            "ruleset_count": 0,
            "errors": [],
        },
    )

    result = runner.invoke(cli, ["repo", "protection", "--repo", "ChatArch/ChatGH"])

    assert result.exit_code == 0
    assert "ChatArch/ChatGH" in result.output
    assert "Default Branch: master" in result.output
    assert "Protected: yes" in result.output
    assert "PR Required: yes" in result.output
    assert "Reviews Required: 0" in result.output


def test_chatgh_repo_protection_renders_owner_inventory(monkeypatch, runner):
    captured = {}

    def fake_inventory(owner, limit, token, jobs):
        captured.update({"owner": owner, "limit": limit, "jobs": jobs})
        return [
            {
                "repo": "ChatArch/ChatGH",
                "default_branch": "master",
                "default_branch_protected": True,
                "branch_protection": {"enabled": True, "required_approving_review_count": 0},
                "ruleset_count": 0,
                "errors": [],
            },
            {
                "repo": "ChatArch/ChatLink",
                "default_branch": "main",
                "default_branch_protected": False,
                "branch_protection": {"enabled": False},
                "ruleset_count": 0,
                "errors": [],
            },
        ]

    monkeypatch.setattr("chatgh.github.cli.list_repo_protections", fake_inventory)

    result = runner.invoke(cli, ["repo", "protection", "--owner", "ChatArch", "--limit", "2", "--jobs", "4"])

    assert result.exit_code == 0
    assert "repo" in result.output
    assert "branch" in result.output
    assert "protected" in result.output
    assert "ChatArch/ChatGH" in result.output
    assert "ChatArch/ChatLink" in result.output
    assert "yes" in result.output
    assert "no" in result.output
    assert captured == {"owner": "ChatArch", "limit": 2, "jobs": 4}


def test_chatgh_repo_protection_inventory_table_preserves_error_text(monkeypatch, runner):
    monkeypatch.setattr(
        "chatgh.github.cli.list_repo_protections",
        lambda owner, limit, token, jobs: [
            {
                "repo": "ChatArch/ChatLink",
                "default_branch": "main",
                "default_branch_protected": False,
                "branch_protection": {"enabled": False},
                "ruleset_count": 0,
                "errors": ["rulesets: Upgrade to GitHub Pro or make this repository public"],
            }
        ],
    )

    result = runner.invoke(cli, ["repo", "protection", "--owner", "ChatArch"])

    assert result.exit_code == 0
    assert "ChatArch/ChatLink" in result.output
    assert "Upgrade to GitHub Pro" in result.output


def test_chatgh_repo_protection_renders_json(monkeypatch, runner):
    monkeypatch.setattr(
        "chatgh.github.cli.inspect_repo_protection",
        lambda repo, token: {
            "repo": repo,
            "default_branch": "master",
            "default_branch_protected": True,
            "branch_protection": {"enabled": True},
            "rulesets": [{"name": "protect-default-branch", "enforcement": "active"}],
            "ruleset_count": 1,
            "errors": [],
        },
    )

    result = runner.invoke(
        cli, ["repo", "protection", "--repo", "ChatArch/ChatGH", "--json-output"]
    )

    assert result.exit_code == 0
    assert '"repo": "ChatArch/ChatGH"' in result.output
    assert '"ruleset_count": 1' in result.output


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


def test_chatgh_repo_fork_defaults_target_name(monkeypatch, runner):
    captured = {}

    def fake_fork(source, owner, name, default_branch_only, if_exists, token):
        captured.update(
            {
                "source": source,
                "owner": owner,
                "name": name,
                "default_branch_only": default_branch_only,
                "if_exists": if_exists,
                "token": token,
            }
        )
        return {
            "full_name": "ChatArch/claude-relay-service",
            "source_full_name": source,
            "created": True,
            "html_url": "https://github.com/ChatArch/claude-relay-service",
        }

    monkeypatch.setattr("chatgh.github.cli.fork_repo", fake_fork)

    result = runner.invoke(
        cli,
        ["repo", "fork", "--source", "Wei-Shaw/claude-relay-service", "--owner", "ChatArch"],
    )

    assert result.exit_code == 0
    assert "forked: ChatArch/claude-relay-service <- Wei-Shaw/claude-relay-service" in result.output
    assert "https://github.com/ChatArch/claude-relay-service" in result.output
    assert captured == {
        "source": "Wei-Shaw/claude-relay-service",
        "owner": "ChatArch",
        "name": None,
        "default_branch_only": False,
        "if_exists": "error",
        "token": None,
    }


def test_chatgh_repo_fork_renders_existing_json(monkeypatch, runner):
    monkeypatch.setattr(
        "chatgh.github.cli.fork_repo",
        lambda source, owner, name, default_branch_only, if_exists, token: {
            "full_name": "ChatArch/claude-relay-service",
            "source_full_name": source,
            "created": False,
            "html_url": "https://github.com/ChatArch/claude-relay-service",
        },
    )

    result = runner.invoke(
        cli,
        [
            "repo",
            "fork",
            "--source",
            "Wei-Shaw/claude-relay-service",
            "--owner",
            "ChatArch",
            "--if-exists",
            "use",
            "--json-output",
        ],
    )

    assert result.exit_code == 0
    assert '"full_name": "ChatArch/claude-relay-service"' in result.output
    assert '"source_full_name": "Wei-Shaw/claude-relay-service"' in result.output
    assert '"created": false' in result.output


def test_chatgh_repo_fork_accepts_gh_like_positional_and_aliases(monkeypatch, runner):
    captured = {}

    def fake_fork(source, owner, name, default_branch_only, if_exists, token):
        captured.update(
            {
                "source": source,
                "owner": owner,
                "name": name,
                "default_branch_only": default_branch_only,
                "if_exists": if_exists,
                "token": token,
            }
        )
        return {
            "full_name": f"{owner}/{name}",
            "source_full_name": source,
            "created": True,
            "html_url": f"https://github.com/{owner}/{name}",
        }

    monkeypatch.setattr("chatgh.github.cli.fork_repo", fake_fork)

    result = runner.invoke(
        cli,
        [
            "repo",
            "fork",
            "Wei-Shaw/claude-relay-service",
            "--org",
            "ChatArch",
            "--fork-name",
            "crs",
            "--default-branch-only",
            "--json-output",
        ],
    )

    assert result.exit_code == 0
    assert '"full_name": "ChatArch/crs"' in result.output
    assert captured == {
        "source": "Wei-Shaw/claude-relay-service",
        "owner": "ChatArch",
        "name": "crs",
        "default_branch_only": True,
        "if_exists": "error",
        "token": None,
    }


def test_chatgh_repo_fork_rejects_conflicting_source_forms(runner):
    result = runner.invoke(
        cli,
        [
            "repo",
            "fork",
            "owner/from-arg",
            "--source",
            "owner/from-option",
            "--owner",
            "ChatArch",
            "-I",
        ],
    )

    assert result.exit_code != 0
    assert "Use either positional repository or --source, not both" in result.output


def test_chatgh_repo_fork_rejects_conflicting_owner_aliases(runner):
    result = runner.invoke(
        cli,
        [
            "repo",
            "fork",
            "owner/repo",
            "--owner",
            "ChatArch",
            "--org",
            "OtherOrg",
            "-I",
        ],
    )

    assert result.exit_code != 0
    assert "Use either --owner or --org, not both" in result.output


def test_chatgh_repo_fork_rejects_conflicting_name_aliases(runner):
    result = runner.invoke(
        cli,
        [
            "repo",
            "fork",
            "owner/repo",
            "--owner",
            "ChatArch",
            "--name",
            "repo-a",
            "--fork-name",
            "repo-b",
            "-I",
        ],
    )

    assert result.exit_code != 0
    assert "Use either --name or --fork-name, not both" in result.output


def test_chatgh_repo_fork_help_uses_gh_like_repository_metavar(runner):
    result = runner.invoke(cli, ["repo", "fork", "--help"])

    assert result.exit_code == 0
    assert "Usage: main repo fork [OPTIONS] REPOSITORY" in result.output
    assert "[SOURCE_ARG]" not in result.output


def test_chatgh_repo_fork_rejects_invalid_source(runner):
    result = runner.invoke(
        cli,
        ["repo", "fork", "--source", "not-a-repo", "--owner", "ChatArch", "-I"],
    )

    assert result.exit_code != 0
    assert "Repo must be in owner/name form" in result.output


def test_post_repo_fork_reuses_existing_matching_fork(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload
            self.ok = 200 <= status_code < 300
            self.text = ""

        def json(self):
            return self._payload

    def fake_get(url, headers, timeout):
        calls.append(("get", url))
        return FakeResponse(
            200,
            {
                "name": "claude-relay-service",
                "full_name": "ChatArch/claude-relay-service",
                "private": False,
                "visibility": "public",
                "stargazers_count": 0,
                "forks_count": 0,
                "open_issues_count": 0,
                "archived": False,
                "fork": True,
                "html_url": "https://github.com/ChatArch/claude-relay-service",
                "clone_url": "https://github.com/ChatArch/claude-relay-service.git",
                "ssh_url": "git@github.com:ChatArch/claude-relay-service.git",
                "default_branch": "main",
                "description": None,
                "source": {"full_name": "Wei-Shaw/claude-relay-service"},
            },
        )

    def fake_post(url, headers, json, timeout):
        calls.append(("post", url))
        raise AssertionError("POST should not run for a matching existing fork")

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("requests.post", fake_post)

    payload = post_repo_fork(
        "Wei-Shaw/claude-relay-service",
        owner="ChatArch",
        name="claude-relay-service",
        default_branch_only=False,
        if_exists="use",
        token="token",
    )

    assert payload["created"] is False
    assert payload["full_name"] == "ChatArch/claude-relay-service"
    assert payload["source_full_name"] == "Wei-Shaw/claude-relay-service"
    assert calls == [("get", "https://api.github.com/repos/ChatArch/claude-relay-service")]


def test_post_repo_fork_rejects_existing_non_fork(monkeypatch):
    class FakeResponse:
        status_code = 200
        ok = True
        text = ""

        def json(self):
            return {
                "name": "claude-relay-service",
                "full_name": "ChatArch/claude-relay-service",
                "fork": False,
            }

    monkeypatch.setattr("requests.get", lambda url, headers, timeout: FakeResponse())

    with pytest.raises(ValueError, match="not a fork of Wei-Shaw/claude-relay-service"):
        post_repo_fork(
            "Wei-Shaw/claude-relay-service",
            owner="ChatArch",
            name="claude-relay-service",
            default_branch_only=False,
            if_exists="use",
            token="token",
        )


def test_post_repo_fork_omits_organization_for_authenticated_user_target(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload
            self.ok = 200 <= status_code < 300
            self.text = ""

        def json(self):
            return self._payload

    def fake_get(url, headers, timeout):
        calls.append(("get", url))
        if url == "https://api.github.com/repos/rex/claude-relay-service":
            return FakeResponse(404, {"message": "Not Found"})
        if url == "https://api.github.com/users/rex":
            return FakeResponse(200, {"login": "rex", "type": "User"})
        if url == "https://api.github.com/user":
            return FakeResponse(200, {"login": "rex"})
        raise AssertionError(f"unexpected GET {url}")

    def fake_post(url, headers, json, timeout):
        calls.append(("post", url, json))
        return FakeResponse(
            202,
            {
                "name": "claude-relay-service",
                "full_name": "rex/claude-relay-service",
                "private": False,
                "fork": True,
                "html_url": "https://github.com/rex/claude-relay-service",
                "source": {"full_name": "Wei-Shaw/claude-relay-service"},
            },
        )

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("requests.post", fake_post)

    payload = post_repo_fork(
        "Wei-Shaw/claude-relay-service",
        owner="rex",
        name="claude-relay-service",
        default_branch_only=True,
        if_exists="error",
        token="token",
    )

    assert payload["created"] is True
    assert ("post", "https://api.github.com/repos/Wei-Shaw/claude-relay-service/forks", {"name": "claude-relay-service", "default_branch_only": True}) in calls


def test_post_repo_fork_includes_organization_for_org_target(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload
            self.ok = 200 <= status_code < 300
            self.text = ""

        def json(self):
            return self._payload

    def fake_get(url, headers, timeout):
        calls.append(("get", url))
        if url == "https://api.github.com/repos/ChatArch/claude-relay-service":
            return FakeResponse(404, {"message": "Not Found"})
        if url == "https://api.github.com/users/ChatArch":
            return FakeResponse(200, {"login": "ChatArch", "type": "Organization"})
        raise AssertionError(f"unexpected GET {url}")

    def fake_post(url, headers, json, timeout):
        calls.append(("post", url, json))
        return FakeResponse(
            202,
            {
                "name": "claude-relay-service",
                "full_name": "ChatArch/claude-relay-service",
                "private": False,
                "fork": True,
                "html_url": "https://github.com/ChatArch/claude-relay-service",
                "source": {"full_name": "Wei-Shaw/claude-relay-service"},
            },
        )

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("requests.post", fake_post)

    payload = post_repo_fork(
        "Wei-Shaw/claude-relay-service",
        owner="ChatArch",
        name="claude-relay-service",
        default_branch_only=False,
        if_exists="error",
        token="token",
    )

    assert payload["created"] is True
    assert (
        "post",
        "https://api.github.com/repos/Wei-Shaw/claude-relay-service/forks",
        {"name": "claude-relay-service", "organization": "ChatArch"},
    ) in calls


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

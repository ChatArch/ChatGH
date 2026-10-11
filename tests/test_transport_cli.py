import json

from click.testing import CliRunner

from chatgh.cli import main


def test_top_level_transport_commands_dispatch_to_importable_api(monkeypatch):
    from chatgh.github import transport_cli

    calls = []
    monkeypatch.setattr(
        transport_cli,
        "fetch",
        lambda remote, refspec, token: calls.append(("fetch", remote, refspec, token))
        or {"remote": remote, "refspec": refspec},
    )
    monkeypatch.setattr(
        transport_cli,
        "pull",
        lambda remote, branch, token, ff_only, rebase: calls.append(
            ("pull", remote, branch, token, ff_only, rebase)
        )
        or {"remote": remote, "branch": branch},
    )
    monkeypatch.setattr(
        transport_cli,
        "push",
        lambda remote, refspec, token, set_upstream, dry_run, tags: calls.append(
            ("push", remote, refspec, token, set_upstream, dry_run, tags)
        )
        or {"remote": remote, "refspec": refspec, "dry_run": dry_run},
    )

    runner = CliRunner()
    fetch_result = runner.invoke(main, ["fetch", "origin", "main", "--token", "explicit"])
    pull_result = runner.invoke(main, ["pull", "origin", "main", "--rebase"])
    push_result = runner.invoke(main, ["push", "origin", "main:main", "-u", "--dry-run"])

    assert fetch_result.exit_code == 0, fetch_result.output
    assert pull_result.exit_code == 0, pull_result.output
    assert push_result.exit_code == 0, push_result.output
    assert calls == [
        ("fetch", "origin", "main", "explicit"),
        ("pull", "origin", "main", None, False, True),
        ("push", "origin", "main:main", None, True, True, False),
    ]
    assert "explicit" not in fetch_result.output


def test_pull_rebase_and_ff_only_are_mutually_exclusive():
    result = CliRunner().invoke(main, ["pull", "--ff-only", "--rebase"])

    assert result.exit_code != 0
    assert "either --ff-only or --rebase" in result.output


def test_unset_token_emits_safe_json_without_a_token(monkeypatch):
    from chatgh.github import transport_cli

    monkeypatch.setattr(
        transport_cli,
        "unset_token",
        lambda: {
            "repo": "acme/repo",
            "removed_keys": ["http.https://github.com/acme/repo.git.extraHeader"],
            "removed_count": 1,
        },
    )

    result = CliRunner().invoke(main, ["unset-token"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "repo": "acme/repo",
        "removed_keys": ["http.https://github.com/acme/repo.git.extraHeader"],
        "removed_count": 1,
    }

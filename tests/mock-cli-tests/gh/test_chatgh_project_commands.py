import json

import pytest
from click.testing import CliRunner

from chatgh.cli import main as cli


pytestmark = pytest.mark.mock_cli


@pytest.fixture
def runner():
    return CliRunner()


def test_project_native_item_and_field_groups_are_registered(runner):
    result = runner.invoke(cli, ["project", "--help"])

    assert result.exit_code == 0
    for command in ["list", "view", "create", "edit", "close", "delete", "copy", "item", "field", "link", "unlink", "mark-template"]:
        assert command in result.output
    for flat_command in [
        "item-list",
        "item-add",
        "item-create",
        "item-edit",
        "item-archive",
        "item-delete",
        "field-list",
        "field-create",
        "field-delete",
    ]:
        assert flat_command not in result.output


def test_project_item_group_commands_are_registered(runner):
    result = runner.invoke(cli, ["project", "item", "--help"])

    assert result.exit_code == 0
    for command in ["list", "add", "create", "edit", "archive", "delete"]:
        assert command in result.output


def test_project_field_group_commands_are_registered(runner):
    result = runner.invoke(cli, ["project", "field", "--help"])

    assert result.exit_code == 0
    for command in ["list", "create", "delete"]:
        assert command in result.output


def test_project_item_edit_expands_item_field_value_options(runner):
    result = runner.invoke(cli, ["project", "item", "edit", "--help"])

    assert result.exit_code == 0
    for option in [
        "--id",
        "--field-id",
        "--field-name",
        "--text",
        "--number",
        "--date",
        "--single-select-option-id",
        "--iteration-id",
        "--clear",
    ]:
        assert option in result.output


def test_project_commands_expose_chatstyle_interactive_flags(runner):
    for args in [
        ["project", "list"],
        ["project", "create"],
        ["project", "view"],
        ["project", "item", "list"],
        ["project", "item", "create"],
        ["project", "field", "list"],
        ["project", "field", "create"],
    ]:
        result = runner.invoke(cli, [*args, "--help"])
        assert result.exit_code == 0, result.output
        assert "-i" in result.output
        assert "-I" in result.output


def test_project_list_prompts_for_missing_owner(monkeypatch, runner):
    captured = {}

    monkeypatch.setattr("chatgh.github.project_cli.is_interactive_available", lambda: True)
    monkeypatch.setattr("chatgh.github.project_cli.ask_text", lambda prompt, **kwargs: "ChatArch")

    def fake_list_projects(owner, limit, closed, token):
        captured.update({"owner": owner, "limit": limit, "closed": closed, "token": token})
        return []

    monkeypatch.setattr("chatgh.github.project_cli.list_projects", fake_list_projects)

    result = runner.invoke(cli, ["project", "list"])

    assert result.exit_code == 0
    assert captured == {"owner": "ChatArch", "limit": 30, "closed": False, "token": None}


def test_project_list_no_interactive_fails_for_missing_owner(runner):
    result = runner.invoke(cli, ["project", "list", "-I"])

    assert result.exit_code != 0
    assert "Missing required value: owner" in result.output


def test_project_list_respects_chatarch_auto_prompt_off(monkeypatch, runner):
    monkeypatch.setenv("CHATARCH_AUTO_PROMPT", "off")
    monkeypatch.setattr("chatgh.github.project_cli.is_interactive_available", lambda: True)
    monkeypatch.setattr("chatgh.github.project_cli.ask_text", lambda prompt, **kwargs: "ChatArch")

    result = runner.invoke(cli, ["project", "list"])

    assert result.exit_code != 0
    assert "Missing required value: owner" in result.output


def test_project_list_force_interactive_ignores_chatarch_auto_prompt_off(monkeypatch, runner):
    captured = {}
    monkeypatch.setenv("CHATARCH_AUTO_PROMPT", "off")
    monkeypatch.setattr("chatgh.github.project_cli.is_interactive_available", lambda: True)
    monkeypatch.setattr("chatgh.github.project_cli.ask_text", lambda prompt, **kwargs: "ChatArch")

    def fake_list_projects(owner, limit, closed, token):
        captured.update({"owner": owner, "limit": limit, "closed": closed, "token": token})
        return []

    monkeypatch.setattr("chatgh.github.project_cli.list_projects", fake_list_projects)

    result = runner.invoke(cli, ["project", "list", "-i"])

    assert result.exit_code == 0
    assert captured["owner"] == "ChatArch"


def test_project_create_prompts_for_missing_owner_and_title(monkeypatch, runner):
    prompts = iter(["ChatArch", "Roadmap"])
    captured = {}

    monkeypatch.setattr("chatgh.github.project_cli.is_interactive_available", lambda: True)
    monkeypatch.setattr("chatgh.github.project_cli.ask_text", lambda prompt, **kwargs: next(prompts))

    def fake_create_project(owner, title, token):
        captured.update({"owner": owner, "title": title, "token": token})
        return {"title": title}

    monkeypatch.setattr("chatgh.github.project_cli.create_project", fake_create_project)

    result = runner.invoke(cli, ["project", "create", "--json-output"])

    assert result.exit_code == 0
    assert captured == {"owner": "ChatArch", "title": "Roadmap", "token": None}
    assert '"Roadmap"' in result.output


def test_project_create_no_interactive_fails_for_missing_owner(runner):
    result = runner.invoke(cli, ["project", "create", "-I"])

    assert result.exit_code != 0
    assert "Missing required value: owner" in result.output


def test_project_delete_interactive_does_not_prompt_for_confirmation(monkeypatch, runner):
    prompts = iter(["3", "ChatArch"])
    called = False

    monkeypatch.setattr("chatgh.github.project_cli.is_interactive_available", lambda: True)
    monkeypatch.setattr("chatgh.github.project_cli.ask_text", lambda prompt, **kwargs: next(prompts))

    def fake_delete_project(owner, number, token):
        nonlocal called
        called = True
        return {"deleted": True}

    monkeypatch.setattr("chatgh.github.project_cli.delete_project", fake_delete_project)

    result = runner.invoke(cli, ["project", "delete", "-i"])

    assert result.exit_code != 0
    assert "--confirm" in result.output
    assert called is False


def test_project_python_api_exports_importable_functions():
    from chatgh.github import projects

    for name in [
        "list_projects",
        "get_project",
        "create_project",
        "update_project",
        "close_project",
        "delete_project",
        "copy_project",
        "list_fields",
        "create_field",
        "delete_field",
        "list_items",
        "add_item",
        "create_draft_item",
        "update_item_field",
        "clear_item_field",
        "archive_item",
        "delete_item",
        "link_repository",
        "unlink_repository",
        "link_team",
        "unlink_team",
        "mark_template",
    ]:
        assert callable(getattr(projects, name))


def test_project_list_dispatches_to_python_api(monkeypatch, runner):
    captured = {}

    def fake_list_projects(owner, limit, closed, token):
        captured.update({"owner": owner, "limit": limit, "closed": closed, "token": token})
        return [{"number": 1, "title": "Roadmap", "url": "https://github.com/orgs/acme/projects/1"}]

    monkeypatch.setattr("chatgh.github.project_cli.list_projects", fake_list_projects)

    result = runner.invoke(cli, ["project", "list", "--owner", "acme", "--limit", "5", "--json-output"])

    assert result.exit_code == 0
    assert captured == {"owner": "acme", "limit": 5, "closed": False, "token": None}
    assert '"title": "Roadmap"' in result.output


def test_project_item_list_dispatches_to_python_api(monkeypatch, runner):
    captured = {}

    def fake_list_items(owner, number, limit, token):
        captured.update({"owner": owner, "number": number, "limit": limit, "token": token})
        return [{"id": "PVTI_1"}]

    monkeypatch.setattr("chatgh.github.project_cli.list_items", fake_list_items)

    result = runner.invoke(cli, ["project", "item", "list", "3", "--owner", "acme", "--limit", "7", "--json-output"])

    assert result.exit_code == 0
    assert captured == {"owner": "acme", "number": 3, "limit": 7, "token": None}
    assert '"PVTI_1"' in result.output


def test_project_item_add_accepts_url(monkeypatch, runner):
    captured = {}

    def fake_add_item(owner, number, url, content_id, token):
        captured.update({"owner": owner, "number": number, "url": url, "content_id": content_id, "token": token})
        return {"id": "PVTI_url"}

    monkeypatch.setattr("chatgh.github.project_cli.add_item", fake_add_item)

    result = runner.invoke(
        cli,
        ["project", "item", "add", "3", "--owner", "acme", "--url", "https://github.com/acme/repo/issues/4", "--json-output"],
    )

    assert result.exit_code == 0
    assert captured == {
        "owner": "acme",
        "number": 3,
        "url": "https://github.com/acme/repo/issues/4",
        "content_id": None,
        "token": None,
    }


def test_project_item_edit_dispatches_field_value_update(monkeypatch, runner):
    captured = {}

    def fake_update_item_field(owner, number, item_id, field_id, value, token):
        captured.update(
            {
                "owner": owner,
                "number": number,
                "item_id": item_id,
                "field_id": field_id,
                "value": value,
                "token": token,
            }
        )
        return {"id": item_id, "field_id": field_id, "value": value}

    monkeypatch.setattr("chatgh.github.project_cli.update_item_field", fake_update_item_field)

    result = runner.invoke(
        cli,
        [
            "project",
            "item",
            "edit",
            "3",
            "--owner",
            "acme",
            "--id",
            "PVTI_123",
            "--field-id",
            "PVTF_456",
            "--text",
            "In progress",
            "--json-output",
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "owner": "acme",
        "number": 3,
        "item_id": "PVTI_123",
        "field_id": "PVTF_456",
        "value": {"text": "In progress"},
        "token": None,
    }
    assert '"PVTI_123"' in result.output


def test_project_delete_requires_confirmation(runner):
    result = runner.invoke(cli, ["project", "delete", "3", "--owner", "acme"])

    assert result.exit_code != 0
    assert "--confirm" in result.output


def test_project_delete_rejects_mismatched_confirmation(monkeypatch, runner):
    called = False

    def fake_delete_project(owner, number, token):
        nonlocal called
        called = True
        return {"deleted": True}

    monkeypatch.setattr("chatgh.github.project_cli.delete_project", fake_delete_project)

    result = runner.invoke(cli, ["project", "delete", "3", "--owner", "acme", "--confirm", "wrong"])

    assert result.exit_code != 0
    assert "must match" in result.output
    assert called is False


def test_project_item_delete_rejects_mismatched_confirmation(monkeypatch, runner):
    called = False

    def fake_delete_item(owner, number, item_id, token):
        nonlocal called
        called = True
        return {"deleted": True}

    monkeypatch.setattr("chatgh.github.project_cli.delete_item", fake_delete_item)

    result = runner.invoke(cli, ["project", "item", "delete", "3", "--owner", "acme", "--id", "PVTI_1", "--confirm", "wrong"])

    assert result.exit_code != 0
    assert "must match" in result.output
    assert called is False


def test_project_field_delete_rejects_mismatched_confirmation(monkeypatch, runner):
    called = False

    def fake_delete_field(owner, field_id, token):
        nonlocal called
        called = True
        return {"deleted": True}

    monkeypatch.setattr("chatgh.github.project_cli.delete_field", fake_delete_field)

    result = runner.invoke(cli, ["project", "field", "delete", "3", "--owner", "acme", "--field-id", "PVTF_1", "--confirm", "wrong"])

    assert result.exit_code != 0
    assert "must match" in result.output
    assert called is False


def test_project_unlink_rejects_mismatched_confirmation(monkeypatch, runner):
    called = False

    def fake_unlink_repository(owner, number, repo_id, token):
        nonlocal called
        called = True
        return {"unlinked": True}

    monkeypatch.setattr("chatgh.github.project_cli.unlink_repository", fake_unlink_repository)

    result = runner.invoke(cli, ["project", "unlink", "3", "--owner", "acme", "--repo-id", "R_1", "--confirm", "wrong"])

    assert result.exit_code != 0
    assert "must match" in result.output
    assert called is False


def test_project_item_edit_resolves_field_name(monkeypatch, runner):
    captured = {}

    monkeypatch.setattr(
        "chatgh.github.project_cli.list_fields",
        lambda owner, number, token: [{"id": 123, "node_id": "PVTF_status", "name": "Status"}],
    )

    def fake_update_item_field(owner, number, item_id, field_id, value, token):
        captured.update({"field_id": field_id, "value": value})
        return {"id": item_id, "field_id": field_id}

    monkeypatch.setattr("chatgh.github.project_cli.update_item_field", fake_update_item_field)

    result = runner.invoke(
        cli,
        [
            "project",
            "item",
            "edit",
            "3",
            "--owner",
            "acme",
            "--id",
            "PVTI_1",
            "--field-name",
            "Status",
            "--text",
            "Done",
            "--json-output",
        ],
    )

    assert result.exit_code == 0
    assert captured == {"field_id": "PVTF_status", "value": {"text": "Done"}}


def test_project_item_edit_rejects_clear_with_value(runner):
    result = runner.invoke(
        cli,
        [
            "project",
            "item",
            "edit",
            "3",
            "--owner",
            "acme",
            "--id",
            "PVTI_1",
            "--field-id",
            "PVTF_status",
            "--clear",
            "--text",
            "Done",
        ],
    )

    assert result.exit_code != 0
    assert "cannot be combined" in result.output


def test_project_item_add_prompts_for_missing_url(monkeypatch, runner):
    prompts = iter(["3", "acme", "https://github.com/acme/repo/issues/4"])
    captured = {}

    monkeypatch.setattr("chatgh.github.project_cli.is_interactive_available", lambda: True)
    monkeypatch.setattr("chatgh.github.project_cli.ask_text", lambda prompt, **kwargs: next(prompts))

    def fake_add_item(owner, number, url, content_id, token):
        captured.update({"owner": owner, "number": number, "url": url, "content_id": content_id, "token": token})
        return {"id": "PVTI_url"}

    monkeypatch.setattr("chatgh.github.project_cli.add_item", fake_add_item)

    result = runner.invoke(cli, ["project", "item", "add", "-i", "--json-output"])

    assert result.exit_code == 0
    assert captured == {
        "owner": "acme",
        "number": 3,
        "url": "https://github.com/acme/repo/issues/4",
        "content_id": None,
        "token": None,
    }


def test_project_item_edit_prompts_for_field_id_and_text_value(monkeypatch, runner):
    prompts = iter(["3", "acme", "PVTI_1", "PVTF_status", "Done"])
    captured = {}

    monkeypatch.setattr("chatgh.github.project_cli.is_interactive_available", lambda: True)
    monkeypatch.setattr("chatgh.github.project_cli.ask_text", lambda prompt, **kwargs: next(prompts))

    def fake_update_item_field(owner, number, item_id, field_id, value, token):
        captured.update({"owner": owner, "number": number, "item_id": item_id, "field_id": field_id, "value": value})
        return {"id": item_id}

    monkeypatch.setattr("chatgh.github.project_cli.update_item_field", fake_update_item_field)

    result = runner.invoke(cli, ["project", "item", "edit", "-i", "--json-output"])

    assert result.exit_code == 0
    assert captured == {"owner": "acme", "number": 3, "item_id": "PVTI_1", "field_id": "PVTF_status", "value": {"text": "Done"}}


def test_project_link_prompts_for_repo_id(monkeypatch, runner):
    prompts = iter(["3", "acme", "R_1"])
    captured = {}

    monkeypatch.setattr("chatgh.github.project_cli.is_interactive_available", lambda: True)
    monkeypatch.setattr("chatgh.github.project_cli.ask_text", lambda prompt, **kwargs: next(prompts))

    def fake_link_repository(owner, number, repo_id, token):
        captured.update({"owner": owner, "number": number, "repo_id": repo_id, "token": token})
        return {"id": repo_id}

    monkeypatch.setattr("chatgh.github.project_cli.link_repository", fake_link_repository)

    result = runner.invoke(cli, ["project", "link", "-i", "--json-output"])

    assert result.exit_code == 0
    assert captured == {"owner": "acme", "number": 3, "repo_id": "R_1", "token": None}


def test_project_unlink_prompts_for_repo_id_but_not_confirm(monkeypatch, runner):
    prompts = iter(["3", "acme", "R_1"])
    captured = {}

    monkeypatch.setattr("chatgh.github.project_cli.is_interactive_available", lambda: True)
    monkeypatch.setattr("chatgh.github.project_cli.ask_text", lambda prompt, **kwargs: next(prompts))

    def fake_unlink_repository(owner, number, repo_id, token):
        captured.update({"owner": owner, "number": number, "repo_id": repo_id, "token": token})
        return {"id": repo_id}

    monkeypatch.setattr("chatgh.github.project_cli.unlink_repository", fake_unlink_repository)

    result = runner.invoke(cli, ["project", "unlink", "-i", "--confirm", "R_1", "--json-output"])

    assert result.exit_code == 0
    assert captured == {"owner": "acme", "number": 3, "repo_id": "R_1", "token": None}


def test_project_field_create_rejects_prompted_invalid_data_type(monkeypatch, runner):
    prompts = iter(["3", "acme", "BadField", "bogus"])
    called = False

    monkeypatch.setattr("chatgh.github.project_cli.is_interactive_available", lambda: True)
    monkeypatch.setattr("chatgh.github.project_cli.ask_text", lambda prompt, **kwargs: next(prompts))

    def fake_create_field(owner, number, name, data_type, options, token):
        nonlocal called
        called = True
        return {"id": "PVTF_bad"}

    monkeypatch.setattr("chatgh.github.project_cli.create_field", fake_create_field)

    result = runner.invoke(cli, ["project", "field", "create", "-i"])

    assert result.exit_code != 0
    assert "Invalid value for --data-type" in result.output
    assert called is False


def test_project_field_list_dispatches_to_python_api(monkeypatch, runner):
    captured = {}

    def fake_list_fields(owner, number, limit, token):
        captured.update({"owner": owner, "number": number, "limit": limit, "token": token})
        return [{"id": "PVTF_1", "name": "Status"}]

    monkeypatch.setattr("chatgh.github.project_cli.list_fields", fake_list_fields)

    result = runner.invoke(cli, ["project", "field", "list", "3", "--owner", "acme", "--limit", "7", "--json-output"])

    assert result.exit_code == 0
    assert captured == {"owner": "acme", "number": 3, "limit": 7, "token": None}
    assert '"PVTF_1"' in result.output

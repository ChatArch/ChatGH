from __future__ import annotations

import json
from typing import Optional

import click

from chatgh.github.projects import (
    add_item,
    archive_item,
    clear_item_field,
    close_project,
    copy_project,
    create_draft_item,
    create_field,
    create_project,
    delete_field,
    delete_item,
    delete_project,
    get_project,
    link_repository,
    link_team,
    list_fields,
    list_items,
    list_projects,
    mark_template,
    unlink_repository,
    unlink_team,
    update_item_field,
    update_project,
)


def _echo_payload(payload, json_output: bool) -> None:
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if isinstance(payload, list):
        for item in payload:
            click.echo(_summary_line(item))
        return
    click.echo(_summary_line(payload))


def _summary_line(item: dict) -> str:
    if not isinstance(item, dict):
        return str(item)
    bits = []
    for key in ("number", "title", "id", "url", "state"):
        if item.get(key) is not None:
            bits.append(f"{key}={item[key]}")
    return "  ".join(bits) if bits else json.dumps(item, ensure_ascii=False)


def _read_text_or_file(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if value.startswith("@"):
        with open(value[1:], encoding="utf-8") as fh:
            return fh.read()
    return value


def _project_value(text, number, date, single_select_option_id, iteration_id):
    provided = [
        text is not None,
        number is not None,
        date is not None,
        single_select_option_id is not None,
        iteration_id is not None,
    ]
    if sum(provided) != 1:
        raise click.ClickException("Pass exactly one field value option: --text, --number, --date, --single-select-option-id, or --iteration-id.")
    if text is not None:
        return {"text": text}
    if number is not None:
        return {"number": number}
    if date is not None:
        return {"date": date}
    if single_select_option_id is not None:
        return {"singleSelectOptionId": single_select_option_id}
    return {"iterationId": iteration_id}


def _has_project_value(text, number, date, single_select_option_id, iteration_id) -> bool:
    return any(
        value is not None
        for value in (text, number, date, single_select_option_id, iteration_id)
    )


def _require_confirmation(confirm: Optional[str], expected: str, label: str) -> None:
    if confirm is None:
        raise click.ClickException(f"{label} is irreversible. Pass --confirm {expected}.")
    if confirm != expected:
        raise click.ClickException(f"--confirm must match {expected}.")


def _resolve_field_id(owner: str, number: int, field_id: Optional[str], field_name: Optional[str], token: Optional[str]) -> str:
    if field_id and field_name:
        raise click.ClickException("Use either --field-id or --field-name, not both.")
    if field_id:
        return field_id
    if not field_name:
        raise click.ClickException("Pass --field-id or --field-name.")
    matches = [field for field in list_fields(owner, number, token) if field.get("name") == field_name]
    if not matches:
        raise click.ClickException(f"Project field not found by name: {field_name}")
    if len(matches) > 1:
        raise click.ClickException(f"Project field name is ambiguous: {field_name}; pass --field-id.")
    resolved = matches[0].get("node_id") or matches[0].get("id")
    if not resolved:
        raise click.ClickException(f"Project field has no id in API response: {field_name}")
    return str(resolved)


@click.group(name="project")
def project_group() -> None:
    """GitHub Projects helpers."""


@project_group.command(name="list")
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--limit", default=30, type=click.IntRange(min=1), show_default=True)
@click.option("--closed", is_flag=True, help="Include closed projects.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_list(owner, limit, closed, json_output, token):
    """List projects for an owner."""
    _echo_payload(list_projects(owner, limit, closed, token), json_output)


@project_group.command(name="view")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_view(number, owner, json_output, token):
    """View a project."""
    _echo_payload(get_project(owner, number, token), json_output)


@project_group.command(name="create")
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--title", required=True, help="Project title.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_create(owner, title, json_output, token):
    """Create a project."""
    _echo_payload(create_project(owner, title, token), json_output)


@project_group.command(name="edit")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--title", default=None, help="Project title.")
@click.option("--description", default=None, help="Project short description.")
@click.option("--readme", default=None, help="Readme text or @file.")
@click.option("--visibility", type=click.Choice(["public", "private"]), default=None)
@click.option("--accept-visibility-change-consequences", is_flag=True, help="Confirm project visibility change.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_edit(number, owner, title, description, readme, visibility, accept_visibility_change_consequences, json_output, token):
    """Edit a project."""
    if visibility is not None and not accept_visibility_change_consequences:
        raise click.ClickException("Changing project visibility may expose or hide project data. Pass --accept-visibility-change-consequences to confirm.")
    _echo_payload(
        update_project(
            owner,
            number,
            title=title,
            short_description=description,
            readme=_read_text_or_file(readme),
            public=(visibility == "public") if visibility else None,
            token=token,
        ),
        json_output,
    )


@project_group.command(name="close")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--undo", is_flag=True, help="Reopen the project.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_close(number, owner, undo, json_output, token):
    """Close or reopen a project."""
    _echo_payload(close_project(owner, number, undo=undo, token=token), json_output)


@project_group.command(name="delete")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--confirm", default=None, help="Confirm by passing the project number or title.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_delete(number, owner, confirm, json_output, token):
    """Delete a project."""
    _require_confirmation(confirm, str(number), "Deleting a project")
    _echo_payload(delete_project(owner, number, token), json_output)


@project_group.command(name="copy")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="Source GitHub user or organization owner.")
@click.option("--target-owner", required=True, help="Target GitHub user or organization owner.")
@click.option("--title", required=True, help="New project title.")
@click.option("--drafts/--no-drafts", default=True, show_default=True, help="Include draft issues.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_copy(number, owner, target_owner, title, drafts, json_output, token):
    """Copy a project."""
    _echo_payload(copy_project(owner, number, target_owner, title, include_draft_issues=drafts, token=token), json_output)


@project_group.command(name="field-list")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_field_list(number, owner, json_output, token):
    """List project fields."""
    _echo_payload(list_fields(owner, number, token), json_output)


@project_group.command(name="field-create")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--name", required=True, help="Field name.")
@click.option("--data-type", type=click.Choice(["text", "number", "date", "single_select", "iteration"]), required=True)
@click.option("--single-select-option", "options", multiple=True, help="Single select option name. Repeatable.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_field_create(number, owner, name, data_type, options, json_output, token):
    """Create a project field."""
    _echo_payload(create_field(owner, number, name, data_type, options=list(options) or None, token=token), json_output)


@project_group.command(name="field-delete")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--field-id", required=True, help="Project field node ID.")
@click.option("--confirm", default=None, help="Confirm by passing the field ID or name.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_field_delete(number, owner, field_id, confirm, json_output, token):
    """Delete a project field."""
    _require_confirmation(confirm, field_id, "Deleting a field")
    _echo_payload(delete_field(owner, field_id, token), json_output)


@project_group.command(name="item-list")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--limit", default=50, type=click.IntRange(min=1), show_default=True)
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_item_list(number, owner, limit, json_output, token):
    """List project items."""
    _echo_payload(list_items(owner, number, limit=limit, token=token), json_output)


@project_group.command(name="item-add")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--url", default=None, help="Issue or pull request URL.")
@click.option("--content-id", default=None, help="Issue or pull request node ID.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_item_add(number, owner, url, content_id, json_output, token):
    """Add an issue or pull request item to a project."""
    _echo_payload(add_item(owner, number, url=url, content_id=content_id, token=token), json_output)


@project_group.command(name="item-create")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--title", required=True, help="Draft issue title.")
@click.option("--body", default=None, help="Draft body text or @file.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_item_create(number, owner, title, body, json_output, token):
    """Create a draft issue item."""
    _echo_payload(create_draft_item(owner, number, title, body=_read_text_or_file(body), token=token), json_output)


@project_group.command(name="item-edit")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--id", "item_id", required=True, help="Project item ID.")
@click.option("--field-id", default=None, help="Project field ID.")
@click.option("--field-name", default=None, help="Project field name (resolved by caller in a later phase).")
@click.option("--text", default=None, help="Set text field value.")
@click.option("--number", "number_value", type=float, default=None, help="Set number field value.")
@click.option("--date", default=None, help="Set date field value (YYYY-MM-DD).")
@click.option("--single-select-option-id", default=None, help="Set single select option ID.")
@click.option("--iteration-id", default=None, help="Set iteration ID.")
@click.option("--clear", is_flag=True, help="Clear the field value.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_item_edit(number, owner, item_id, field_id, field_name, text, number_value, date, single_select_option_id, iteration_id, clear, json_output, token):
    """Edit a project item field value."""
    field = _resolve_field_id(owner, number, field_id, field_name, token)
    if clear:
        if _has_project_value(text, number_value, date, single_select_option_id, iteration_id):
            raise click.ClickException("--clear cannot be combined with field value options.")
        _echo_payload(clear_item_field(owner, number, item_id, field, token), json_output)
        return
    value = _project_value(text, number_value, date, single_select_option_id, iteration_id)
    _echo_payload(update_item_field(owner, number, item_id, field, value, token), json_output)


@project_group.command(name="item-archive")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--id", "item_id", required=True, help="Project item ID.")
@click.option("--undo", is_flag=True, help="Unarchive the item.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_item_archive(number, owner, item_id, undo, json_output, token):
    """Archive or unarchive a project item."""
    _echo_payload(archive_item(owner, number, item_id, undo=undo, token=token), json_output)


@project_group.command(name="item-delete")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--id", "item_id", required=True, help="Project item ID.")
@click.option("--confirm", default=None, help="Confirm by passing the item ID.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_item_delete(number, owner, item_id, confirm, json_output, token):
    """Delete a project item."""
    _require_confirmation(confirm, item_id, "Deleting an item")
    _echo_payload(delete_item(owner, number, item_id, token), json_output)


@project_group.command(name="link")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--repo-id", default=None, help="Repository node ID.")
@click.option("--team-id", default=None, help="Team node ID.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_link(number, owner, repo_id, team_id, json_output, token):
    """Link a repository or team to a project."""
    if bool(repo_id) == bool(team_id):
        raise click.ClickException("Pass exactly one of --repo-id or --team-id.")
    payload = link_repository(owner, number, repo_id, token) if repo_id else link_team(owner, number, team_id, token)
    _echo_payload(payload, json_output)


@project_group.command(name="unlink")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--repo-id", default=None, help="Repository node ID.")
@click.option("--team-id", default=None, help="Team node ID.")
@click.option("--confirm", default=None, help="Confirm target ID.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_unlink(number, owner, repo_id, team_id, confirm, json_output, token):
    """Unlink a repository or team from a project."""
    if bool(repo_id) == bool(team_id):
        raise click.ClickException("Pass exactly one of --repo-id or --team-id.")
    target = repo_id or team_id
    _require_confirmation(confirm, target, "Unlinking changes project visibility/scope")
    payload = unlink_repository(owner, number, repo_id, token) if repo_id else unlink_team(owner, number, team_id, token)
    _echo_payload(payload, json_output)


@project_group.command(name="mark-template")
@click.argument("number", type=int)
@click.option("--owner", required=True, help="GitHub user or organization owner.")
@click.option("--undo", is_flag=True, help="Unmark as template.")
@click.option("--json-output", is_flag=True, help="Output JSON.")
@click.option("--token", default=None, help="GitHub token.")
def project_mark_template(number, owner, undo, json_output, token):
    """Mark or unmark a project as a template."""
    _echo_payload(mark_template(owner, number, undo=undo, token=token), json_output)

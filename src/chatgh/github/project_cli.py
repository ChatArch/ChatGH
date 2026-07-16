from __future__ import annotations

import json
import os
from typing import Optional

import click
from chatstyle import CommandField, CommandSchema, add_interactive_option, resolve_command_inputs
from chatstyle.core import InteractiveResolution, normalize_interactive
from chatstyle.core.interactive import is_interactive_available
from chatstyle.tui.prompt import ask_text

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


OWNER_SCHEMA = CommandSchema(
    name="project-owner",
    fields=(CommandField("owner", prompt="GitHub owner or organization", required=True),),
)

PROJECT_REF_SCHEMA = CommandSchema(
    name="project-ref",
    fields=(
        CommandField("number", prompt="project number", kind="int", required=True),
        CommandField("owner", prompt="GitHub owner or organization", required=True),
    ),
)

PROJECT_CREATE_SCHEMA = CommandSchema(
    name="project-create",
    fields=(
        CommandField("owner", prompt="GitHub owner or organization", required=True),
        CommandField("title", prompt="project title", required=True),
    ),
)

PROJECT_COPY_SCHEMA = CommandSchema(
    name="project-copy",
    fields=(
        CommandField("number", prompt="project number", kind="int", required=True),
        CommandField("owner", prompt="source GitHub owner or organization", required=True),
        CommandField("target_owner", prompt="target GitHub owner or organization", required=True),
        CommandField("title", prompt="new project title", required=True),
    ),
)

PROJECT_FIELD_SCHEMA = CommandSchema(
    name="project-field",
    fields=(
        CommandField("number", prompt="project number", kind="int", required=True),
        CommandField("owner", prompt="GitHub owner or organization", required=True),
        CommandField("field_id", prompt="project field node ID", required=True),
    ),
)

PROJECT_ITEM_SCHEMA = CommandSchema(
    name="project-item",
    fields=(
        CommandField("number", prompt="project number", kind="int", required=True),
        CommandField("owner", prompt="GitHub owner or organization", required=True),
        CommandField("item_id", prompt="project item node ID", required=True),
    ),
)

PROJECT_ITEM_CREATE_SCHEMA = CommandSchema(
    name="project-item-create",
    fields=(
        CommandField("number", prompt="project number", kind="int", required=True),
        CommandField("owner", prompt="GitHub owner or organization", required=True),
        CommandField("title", prompt="draft item title", required=True),
    ),
)

PROJECT_FIELD_CREATE_SCHEMA = CommandSchema(
    name="project-field-create",
    fields=(
        CommandField("number", prompt="project number", kind="int", required=True),
        CommandField("owner", prompt="GitHub owner or organization", required=True),
        CommandField("name", prompt="field name", required=True),
        CommandField("data_type", prompt="field data type", required=True),
    ),
)

PROJECT_ITEM_ADD_SCHEMA = CommandSchema(
    name="project-item-add",
    fields=(
        CommandField("number", prompt="project number", kind="int", required=True),
        CommandField("owner", prompt="GitHub owner or organization", required=True),
    ),
)

PROJECT_LINK_SCHEMA = CommandSchema(
    name="project-link",
    fields=(
        CommandField("number", prompt="project number", kind="int", required=True),
        CommandField("owner", prompt="GitHub owner or organization", required=True),
    ),
)

PROJECT_ITEM_URL_SCHEMA = CommandSchema(
    name="project-item-url",
    fields=(CommandField("url", prompt="issue or pull request URL", required=True),),
)

PROJECT_ITEM_FIELD_ID_SCHEMA = CommandSchema(
    name="project-item-field-id",
    fields=(CommandField("field_id", prompt="project field node ID", required=True),),
)

PROJECT_ITEM_TEXT_VALUE_SCHEMA = CommandSchema(
    name="project-item-text-value",
    fields=(CommandField("text", prompt="text field value", required=True),),
)

PROJECT_REPO_ID_SCHEMA = CommandSchema(
    name="project-repo-id",
    fields=(CommandField("repo_id", prompt="repository node ID", required=True),),
)


AUTO_PROMPT_ENV_VAR = "CHATARCH_AUTO_PROMPT"
FALSE_AUTO_PROMPT_VALUES = {"0", "false", "no", "off"}


def auto_prompt_enabled() -> bool:
    value = os.getenv(AUTO_PROMPT_ENV_VAR)
    if value is None:
        return True
    return value.strip().lower() not in FALSE_AUTO_PROMPT_VALUES


class _TextPromptRuntime:
    def ask_text(self, prompt: str, default: str = "", password: bool = False):
        return ask_text(prompt, default=default, password=password)


TEXT_PROMPT_RUNTIME = _TextPromptRuntime()


def resolve_cli_interactive_mode(interactive: bool | None, *, auto_prompt_condition: bool):
    interactive = normalize_interactive(interactive)
    can_prompt = is_interactive_available()
    force_interactive = interactive is True
    need_prompt = force_interactive or (interactive is None and auto_prompt_condition and auto_prompt_enabled() and can_prompt)
    return InteractiveResolution(
        interactive=interactive,
        can_prompt=can_prompt,
        force_interactive=force_interactive,
        need_prompt=need_prompt,
    )


def _resolve_inputs(schema: CommandSchema, provided: dict, interactive: bool | None, usage: str) -> dict:
    return resolve_command_inputs(
        schema=schema,
        provided=provided,
        interactive=interactive,
        usage=usage,
        prompt_runtime_override=TEXT_PROMPT_RUNTIME,
        interactive_resolver_override=resolve_cli_interactive_mode,
    )


def _resolve_optional_input(schema: CommandSchema, provided: dict, interactive: bool | None, usage: str) -> dict:
    return _resolve_inputs(schema, provided, interactive, usage)


def _validate_field_data_type(data_type: str) -> str:
    choices = {"text", "number", "date", "single_select", "iteration"}
    if data_type not in choices:
        ordered = ", ".join(sorted(choices))
        raise click.ClickException(f"Invalid value for --data-type: {data_type}. Choose from: {ordered}.")
    return data_type


def _echo_payload(payload, json_fields: str | None, json_output: bool) -> None:
    from chatgh.github.render import echo_json_if_requested

    if echo_json_if_requested(payload, json_fields, json_output):
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
    matches = [field for field in list_fields(owner, number, token=token) if field.get("name") == field_name]
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


@project_group.group(name="item")
def project_item_group() -> None:
    """Manage project items."""


@project_group.group(name="field")
def project_field_group() -> None:
    """Manage project fields."""


@project_group.command(name="list")
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--limit", default=30, type=click.IntRange(min=1), show_default=True)
@click.option("--closed", is_flag=True, help="Include closed projects.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_list(owner, limit, closed, json_fields, json_output, token, interactive):
    """List projects for an owner."""
    inputs = _resolve_inputs(OWNER_SCHEMA, {"owner": owner}, interactive, "Usage: chatgh project list --owner OWNER [-i|-I]")
    _echo_payload(list_projects(inputs["owner"], limit, closed, token), json_fields, json_output)


@project_group.command(name="view")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_view(number, owner, json_fields, json_output, token, interactive):
    """View a project."""
    inputs = _resolve_inputs(PROJECT_REF_SCHEMA, {"number": number, "owner": owner}, interactive, "Usage: chatgh project view NUMBER --owner OWNER [-i|-I]")
    _echo_payload(get_project(inputs["owner"], int(inputs["number"]), token), json_fields, json_output)


@project_group.command(name="create")
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--title", required=False, help="Project title.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_create(owner, title, json_fields, json_output, token, interactive):
    """Create a project."""
    inputs = _resolve_inputs(PROJECT_CREATE_SCHEMA, {"owner": owner, "title": title}, interactive, "Usage: chatgh project create --owner OWNER --title TITLE [-i|-I]")
    _echo_payload(create_project(inputs["owner"], inputs["title"], token), json_fields, json_output)


@project_group.command(name="edit")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--title", default=None, help="Project title.")
@click.option("--description", default=None, help="Project short description.")
@click.option("--readme", default=None, help="Readme text or @file.")
@click.option("--visibility", type=click.Choice(["public", "private"]), default=None)
@click.option("--accept-visibility-change-consequences", is_flag=True, help="Confirm project visibility change.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_edit(number, owner, title, description, readme, visibility, accept_visibility_change_consequences, json_fields, json_output, token, interactive):
    """Edit a project."""
    inputs = _resolve_inputs(PROJECT_REF_SCHEMA, {"number": number, "owner": owner}, interactive, "Usage: chatgh project edit NUMBER --owner OWNER [-i|-I]")
    if visibility is not None and not accept_visibility_change_consequences:
        raise click.ClickException("Changing project visibility may expose or hide project data. Pass --accept-visibility-change-consequences to confirm.")
    _echo_payload(
        update_project(
            inputs["owner"],
            int(inputs["number"]),
            title=title,
            short_description=description,
            readme=_read_text_or_file(readme),
            public=(visibility == "public") if visibility else None,
            token=token,
        ),
        json_fields,
        json_output,
    )


@project_group.command(name="close")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--undo", is_flag=True, help="Reopen the project.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_close(number, owner, undo, json_fields, json_output, token, interactive):
    """Close or reopen a project."""
    inputs = _resolve_inputs(PROJECT_REF_SCHEMA, {"number": number, "owner": owner}, interactive, "Usage: chatgh project close NUMBER --owner OWNER [-i|-I]")
    _echo_payload(close_project(inputs["owner"], int(inputs["number"]), undo=undo, token=token), json_fields, json_output)


@project_group.command(name="delete")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--confirm", default=None, help="Confirm by passing the project number or title.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_delete(number, owner, confirm, json_fields, json_output, token, interactive):
    """Delete a project."""
    inputs = _resolve_inputs(PROJECT_REF_SCHEMA, {"number": number, "owner": owner}, interactive, "Usage: chatgh project delete NUMBER --owner OWNER --confirm NUMBER [-i|-I]")
    project_number = int(inputs["number"])
    _require_confirmation(confirm, str(project_number), "Deleting a project")
    _echo_payload(delete_project(inputs["owner"], project_number, token), json_fields, json_output)


@project_group.command(name="copy")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="Source GitHub user or organization owner.")
@click.option("--target-owner", required=False, help="Target GitHub user or organization owner.")
@click.option("--title", required=False, help="New project title.")
@click.option("--drafts/--no-drafts", default=True, show_default=True, help="Include draft issues.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_copy(number, owner, target_owner, title, drafts, json_fields, json_output, token, interactive):
    """Copy a project."""
    inputs = _resolve_inputs(PROJECT_COPY_SCHEMA, {"number": number, "owner": owner, "target_owner": target_owner, "title": title}, interactive, "Usage: chatgh project copy NUMBER --owner OWNER --target-owner OWNER --title TITLE [-i|-I]")
    _echo_payload(copy_project(inputs["owner"], int(inputs["number"]), inputs["target_owner"], inputs["title"], include_draft_issues=drafts, token=token), json_fields, json_output)


@project_field_group.command(name="list")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--limit", default=50, type=click.IntRange(min=1), show_default=True)
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_field_list(number, owner, limit, json_fields, json_output, token, interactive):
    """List project fields."""
    inputs = _resolve_inputs(PROJECT_REF_SCHEMA, {"number": number, "owner": owner}, interactive, "Usage: chatgh project field list NUMBER --owner OWNER [-i|-I]")
    _echo_payload(list_fields(inputs["owner"], int(inputs["number"]), limit=limit, token=token), json_fields, json_output)


@project_field_group.command(name="create")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--name", required=False, help="Field name.")
@click.option("--data-type", type=click.Choice(["text", "number", "date", "single_select", "iteration"]), required=False)
@click.option("--single-select-option", "options", multiple=True, help="Single select option name. Repeatable.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_field_create(number, owner, name, data_type, options, json_fields, json_output, token, interactive):
    """Create a project field."""
    inputs = _resolve_inputs(PROJECT_FIELD_CREATE_SCHEMA, {"number": number, "owner": owner, "name": name, "data_type": data_type}, interactive, "Usage: chatgh project field create NUMBER --owner OWNER --name NAME --data-type TYPE [-i|-I]")
    data_type_value = _validate_field_data_type(inputs["data_type"])
    _echo_payload(create_field(inputs["owner"], int(inputs["number"]), inputs["name"], data_type_value, options=list(options) or None, token=token), json_fields, json_output)


@project_field_group.command(name="delete")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--field-id", required=False, help="Project field node ID.")
@click.option("--confirm", default=None, help="Confirm by passing the field ID or name.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_field_delete(number, owner, field_id, confirm, json_fields, json_output, token, interactive):
    """Delete a project field."""
    inputs = _resolve_inputs(PROJECT_FIELD_SCHEMA, {"number": number, "owner": owner, "field_id": field_id}, interactive, "Usage: chatgh project field delete NUMBER --owner OWNER --field-id FIELD_ID --confirm FIELD_ID [-i|-I]")
    _require_confirmation(confirm, inputs["field_id"], "Deleting a field")
    _echo_payload(delete_field(inputs["owner"], inputs["field_id"], token), json_fields, json_output)


@project_item_group.command(name="list")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--limit", default=50, type=click.IntRange(min=1), show_default=True)
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_item_list(number, owner, limit, json_fields, json_output, token, interactive):
    """List project items."""
    inputs = _resolve_inputs(PROJECT_REF_SCHEMA, {"number": number, "owner": owner}, interactive, "Usage: chatgh project item list NUMBER --owner OWNER [-i|-I]")
    _echo_payload(list_items(inputs["owner"], int(inputs["number"]), limit=limit, token=token), json_fields, json_output)


@project_item_group.command(name="add")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--url", default=None, help="Issue or pull request URL.")
@click.option("--content-id", default=None, help="Issue or pull request node ID.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_item_add(number, owner, url, content_id, json_fields, json_output, token, interactive):
    """Add an issue or pull request item to a project."""
    inputs = _resolve_inputs(PROJECT_ITEM_ADD_SCHEMA, {"number": number, "owner": owner}, interactive, "Usage: chatgh project item add NUMBER --owner OWNER (--url URL|--content-id ID) [-i|-I]")
    if not url and not content_id:
        extra_inputs = _resolve_optional_input(PROJECT_ITEM_URL_SCHEMA, {"url": url}, interactive, "Usage: chatgh project item add NUMBER --owner OWNER (--url URL|--content-id ID) [-i|-I]")
        url = extra_inputs["url"]
    _echo_payload(add_item(inputs["owner"], int(inputs["number"]), url=url, content_id=content_id, token=token), json_fields, json_output)


@project_item_group.command(name="create")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--title", required=False, help="Draft issue title.")
@click.option("--body", default=None, help="Draft body text or @file.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_item_create(number, owner, title, body, json_fields, json_output, token, interactive):
    """Create a draft issue item."""
    inputs = _resolve_inputs(PROJECT_ITEM_CREATE_SCHEMA, {"number": number, "owner": owner, "title": title}, interactive, "Usage: chatgh project item create NUMBER --owner OWNER --title TITLE [-i|-I]")
    _echo_payload(create_draft_item(inputs["owner"], int(inputs["number"]), inputs["title"], body=_read_text_or_file(body), token=token), json_fields, json_output)


@project_item_group.command(name="edit")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--id", "item_id", required=False, help="Project item ID.")
@click.option("--field-id", default=None, help="Project field ID.")
@click.option("--field-name", default=None, help="Project field name (resolved by caller in a later phase).")
@click.option("--text", default=None, help="Set text field value.")
@click.option("--number", "number_value", type=float, default=None, help="Set number field value.")
@click.option("--date", default=None, help="Set date field value (YYYY-MM-DD).")
@click.option("--single-select-option-id", default=None, help="Set single select option ID.")
@click.option("--iteration-id", default=None, help="Set iteration ID.")
@click.option("--clear", is_flag=True, help="Clear the field value.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_item_edit(number, owner, item_id, field_id, field_name, text, number_value, date, single_select_option_id, iteration_id, clear, json_fields, json_output, token, interactive):
    """Edit a project item field value."""
    inputs = _resolve_inputs(PROJECT_ITEM_SCHEMA, {"number": number, "owner": owner, "item_id": item_id}, interactive, "Usage: chatgh project item edit NUMBER --owner OWNER --id ITEM_ID (--field-id ID|--field-name NAME) [-i|-I]")
    owner = inputs["owner"]
    number = int(inputs["number"])
    item_id = inputs["item_id"]
    if not field_id and not field_name:
        field_inputs = _resolve_optional_input(PROJECT_ITEM_FIELD_ID_SCHEMA, {"field_id": field_id}, interactive, "Usage: chatgh project item edit NUMBER --owner OWNER --id ITEM_ID (--field-id ID|--field-name NAME) [-i|-I]")
        field_id = field_inputs["field_id"]
    if not clear and not _has_project_value(text, number_value, date, single_select_option_id, iteration_id):
        value_inputs = _resolve_optional_input(PROJECT_ITEM_TEXT_VALUE_SCHEMA, {"text": text}, interactive, "Usage: chatgh project item edit NUMBER --owner OWNER --id ITEM_ID --field-id FIELD_ID --text TEXT [-i|-I]")
        text = value_inputs["text"]
    field = _resolve_field_id(owner, number, field_id, field_name, token)
    if clear:
        if _has_project_value(text, number_value, date, single_select_option_id, iteration_id):
            raise click.ClickException("--clear cannot be combined with field value options.")
        _echo_payload(clear_item_field(owner, number, item_id, field, token), json_fields, json_output)
        return
    value = _project_value(text, number_value, date, single_select_option_id, iteration_id)
    _echo_payload(update_item_field(owner, number, item_id, field, value, token), json_fields, json_output)


@project_item_group.command(name="archive")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--id", "item_id", required=False, help="Project item ID.")
@click.option("--undo", is_flag=True, help="Unarchive the item.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_item_archive(number, owner, item_id, undo, json_fields, json_output, token, interactive):
    """Archive or unarchive a project item."""
    inputs = _resolve_inputs(PROJECT_ITEM_SCHEMA, {"number": number, "owner": owner, "item_id": item_id}, interactive, "Usage: chatgh project item archive NUMBER --owner OWNER --id ITEM_ID [-i|-I]")
    _echo_payload(archive_item(inputs["owner"], int(inputs["number"]), inputs["item_id"], undo=undo, token=token), json_fields, json_output)


@project_item_group.command(name="delete")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--id", "item_id", required=False, help="Project item ID.")
@click.option("--confirm", default=None, help="Confirm by passing the item ID.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_item_delete(number, owner, item_id, confirm, json_fields, json_output, token, interactive):
    """Delete a project item."""
    inputs = _resolve_inputs(PROJECT_ITEM_SCHEMA, {"number": number, "owner": owner, "item_id": item_id}, interactive, "Usage: chatgh project item delete NUMBER --owner OWNER --id ITEM_ID --confirm ITEM_ID [-i|-I]")
    _require_confirmation(confirm, inputs["item_id"], "Deleting an item")
    _echo_payload(delete_item(inputs["owner"], int(inputs["number"]), inputs["item_id"], token), json_fields, json_output)


@project_group.command(name="link")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--repo-id", default=None, help="Repository node ID.")
@click.option("--team-id", default=None, help="Team node ID.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_link(number, owner, repo_id, team_id, json_fields, json_output, token, interactive):
    """Link a repository or team to a project."""
    inputs = _resolve_inputs(PROJECT_LINK_SCHEMA, {"number": number, "owner": owner}, interactive, "Usage: chatgh project link NUMBER --owner OWNER (--repo-id ID|--team-id ID) [-i|-I]")
    if not repo_id and not team_id:
        repo_inputs = _resolve_optional_input(PROJECT_REPO_ID_SCHEMA, {"repo_id": repo_id}, interactive, "Usage: chatgh project link NUMBER --owner OWNER (--repo-id ID|--team-id ID) [-i|-I]")
        repo_id = repo_inputs["repo_id"]
    if bool(repo_id) == bool(team_id):
        raise click.ClickException("Pass exactly one of --repo-id or --team-id.")
    payload = link_repository(inputs["owner"], int(inputs["number"]), repo_id, token) if repo_id else link_team(inputs["owner"], int(inputs["number"]), team_id, token)
    _echo_payload(payload, json_fields, json_output)


@project_group.command(name="unlink")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--repo-id", default=None, help="Repository node ID.")
@click.option("--team-id", default=None, help="Team node ID.")
@click.option("--confirm", default=None, help="Confirm target ID.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_unlink(number, owner, repo_id, team_id, confirm, json_fields, json_output, token, interactive):
    """Unlink a repository or team from a project."""
    inputs = _resolve_inputs(PROJECT_LINK_SCHEMA, {"number": number, "owner": owner}, interactive, "Usage: chatgh project unlink NUMBER --owner OWNER (--repo-id ID|--team-id ID) --confirm ID [-i|-I]")
    if not repo_id and not team_id:
        repo_inputs = _resolve_optional_input(PROJECT_REPO_ID_SCHEMA, {"repo_id": repo_id}, interactive, "Usage: chatgh project unlink NUMBER --owner OWNER (--repo-id ID|--team-id ID) --confirm ID [-i|-I]")
        repo_id = repo_inputs["repo_id"]
    if bool(repo_id) == bool(team_id):
        raise click.ClickException("Pass exactly one of --repo-id or --team-id.")
    target = repo_id or team_id
    _require_confirmation(confirm, target, "Unlinking changes project visibility/scope")
    payload = unlink_repository(inputs["owner"], int(inputs["number"]), repo_id, token) if repo_id else unlink_team(inputs["owner"], int(inputs["number"]), team_id, token)
    _echo_payload(payload, json_fields, json_output)


@project_group.command(name="mark-template")
@click.argument("number", required=False, type=int)
@click.option("--owner", required=False, help="GitHub user or organization owner.")
@click.option("--undo", is_flag=True, help="Unmark as template.")
@click.option("--json", "json_fields", metavar="FIELDS", default=None, help="Output JSON with specified fields.")
@click.option("--json-output", is_flag=True, help="Output full JSON payload.")
@click.option("--token", default=None, help="GitHub token.")
@add_interactive_option
def project_mark_template(number, owner, undo, json_fields, json_output, token, interactive):
    """Mark or unmark a project as a template."""
    inputs = _resolve_inputs(PROJECT_REF_SCHEMA, {"number": number, "owner": owner}, interactive, "Usage: chatgh project mark-template NUMBER --owner OWNER [-i|-I]")
    _echo_payload(mark_template(inputs["owner"], int(inputs["number"]), undo=undo, token=token), json_fields, json_output)

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlparse

import click

from chatgh.github.api import credential_path_from_repo, github_api_headers, resolve_token

GRAPHQL_URL = "https://api.github.com/graphql"


def _resolved_token(owner: str, token: Optional[str]) -> Optional[str]:
    return resolve_token(token, credential_path=credential_path_from_repo(f"{owner}/_"))


def _rest_request(method: str, path: str, token: Optional[str], *, json_payload: Optional[dict] = None, params: Optional[dict] = None) -> Any:
    import requests

    url = f"https://api.github.com{path}"
    try:
        response = requests.request(
            method,
            url,
            headers=github_api_headers(token),
            json=json_payload,
            params=params,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise click.ClickException(f"GitHub API request failed for {path}: {exc}") from exc
    if response.status_code == 204:
        return {"deleted": True, "path": path}
    if response.ok:
        try:
            return response.json()
        except ValueError as exc:
            raise click.ClickException(f"GitHub API returned non-JSON response for {path}") from exc
    detail = _response_detail(response)
    raise click.ClickException(f"GitHub API error ({response.status_code}) for {path}: {detail}")


def _rest_request_owner(method: str, owner: str, suffix: str, token: Optional[str], *, json_payload: Optional[dict] = None, params: Optional[dict] = None) -> Any:
    org_path = f"/orgs/{owner}{suffix}"
    try:
        return _rest_request(method, org_path, token, json_payload=json_payload, params=params)
    except click.ClickException as org_exc:
        if "(404)" not in str(org_exc):
            raise
    user_path = f"/users/{owner}{suffix}"
    return _rest_request(method, user_path, token, json_payload=json_payload, params=params)


def _graphql(owner: str, query: str, variables: dict, token: Optional[str]) -> dict:
    import requests

    resolved = _resolved_token(owner, token)
    if not resolved:
        raise click.ClickException("Missing token. Pass --token or configure a ChatGH GitHub credential.")
    try:
        response = requests.post(
            GRAPHQL_URL,
            headers=github_api_headers(resolved),
            json={"query": query, "variables": variables},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise click.ClickException(f"GitHub GraphQL request failed: {exc}") from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise click.ClickException("GitHub GraphQL returned non-JSON response") from exc
    if not response.ok or payload.get("errors"):
        detail = payload.get("errors") or _response_detail(response)
        raise click.ClickException(f"GitHub GraphQL error ({response.status_code}): {detail}")
    return payload.get("data") or {}


def _response_detail(response) -> str:
    detail = (response.text or "").strip()
    try:
        payload = response.json()
        if isinstance(payload, dict) and payload.get("message"):
            detail = str(payload["message"])
    except ValueError:
        pass
    return detail or "unknown error"


def _normalize_node_payload(item: dict) -> dict:
    """Prefer GraphQL node IDs in the public payload while preserving REST IDs.

    GitHub Projects v2 REST endpoints commonly return integer ``id`` fields plus
    GraphQL ``node_id`` values. Most follow-up mutations require node IDs, so the
    ChatGH public payload uses ``id`` for the node ID and preserves the REST
    integer as ``database_id``.
    """
    if not isinstance(item, dict):
        return item
    if item.get("node_id") and item.get("id") != item.get("node_id"):
        normalized = dict(item)
        normalized["database_id"] = item.get("id")
        normalized["id"] = item.get("node_id")
        return normalized
    return item


def _project_id(owner: str, number: int | str, token: Optional[str]) -> str:
    if str(number).startswith("PVT"):
        return str(number)
    query = """
    query($owner:String!, $number:Int!) {
      organization(login:$owner) { projectV2(number:$number) { id } }
      user(login:$owner) { projectV2(number:$number) { id } }
    }
    """
    data = _graphql(owner, query, {"owner": owner, "number": int(number)}, token)
    project = ((data.get("organization") or {}).get("projectV2") or (data.get("user") or {}).get("projectV2") or {})
    project_id = project.get("id")
    if not project_id:
        raise click.ClickException(f"Project not found: {owner}/{number}")
    return str(project_id)


def _owner_id(owner: str, token: Optional[str]) -> str:
    query = """
    query($owner:String!) {
      organization(login:$owner) { id }
      user(login:$owner) { id }
    }
    """
    data = _graphql(owner, query, {"owner": owner}, token)
    owner_id = ((data.get("organization") or {}).get("id") or (data.get("user") or {}).get("id"))
    if not owner_id:
        raise click.ClickException(f"GitHub owner not found: {owner}")
    return str(owner_id)


def list_projects(owner: str, limit: int = 30, closed: bool = False, token: Optional[str] = None) -> list[dict]:
    resolved = _resolved_token(owner, token)
    payload = _rest_request_owner("GET", owner, "/projectsV2", resolved, params={"per_page": limit})
    items = payload if isinstance(payload, list) else payload.get("projects", []) if isinstance(payload, dict) else []
    if closed:
        return list(items)
    return [item for item in items if not item.get("closed")]


def get_project(owner: str, number: int | str, token: Optional[str] = None) -> dict:
    resolved = _resolved_token(owner, token)
    return _rest_request_owner("GET", owner, f"/projectsV2/{int(number)}", resolved)


def create_project(owner: str, title: str, token: Optional[str] = None) -> dict:
    owner_id = _owner_id(owner, token)
    query = """
    mutation($input:CreateProjectV2Input!) {
      createProjectV2(input:$input) { projectV2 { id number title url } }
    }
    """
    data = _graphql(owner, query, {"input": {"ownerId": owner_id, "title": title}}, token)
    return (data.get("createProjectV2") or {}).get("projectV2") or {}


def update_project(owner: str, number: int | str, *, title: Optional[str] = None, short_description: Optional[str] = None, readme: Optional[str] = None, public: Optional[bool] = None, closed: Optional[bool] = None, token: Optional[str] = None) -> dict:
    project_id = _project_id(owner, number, token)
    input_payload: dict[str, Any] = {"projectId": project_id}
    if title is not None:
        input_payload["title"] = title
    if short_description is not None:
        input_payload["shortDescription"] = short_description
    if readme is not None:
        input_payload["readme"] = readme
    if public is not None:
        input_payload["public"] = public
    if closed is not None:
        input_payload["closed"] = closed
    query = """
    mutation($input:UpdateProjectV2Input!) {
      updateProjectV2(input:$input) { projectV2 { id number title url closed public } }
    }
    """
    data = _graphql(owner, query, {"input": input_payload}, token)
    return (data.get("updateProjectV2") or {}).get("projectV2") or {}


def close_project(owner: str, number: int | str, *, undo: bool = False, token: Optional[str] = None) -> dict:
    return update_project(owner, number, closed=not undo, token=token)


def delete_project(owner: str, number: int | str, token: Optional[str] = None) -> dict:
    project_id = _project_id(owner, number, token)
    query = "mutation($input:DeleteProjectV2Input!) { deleteProjectV2(input:$input) { projectV2 { id } } }"
    data = _graphql(owner, query, {"input": {"projectId": project_id}}, token)
    return {"deleted": True, "project": (data.get("deleteProjectV2") or {}).get("projectV2")}


def copy_project(owner: str, number: int | str, target_owner: str, title: str, *, include_draft_issues: bool = True, token: Optional[str] = None) -> dict:
    project_id = _project_id(owner, number, token)
    owner_id = _owner_id(target_owner, token)
    query = """
    mutation($input:CopyProjectV2Input!) {
      copyProjectV2(input:$input) { projectV2 { id number title url } }
    }
    """
    variables = {"input": {"projectId": project_id, "ownerId": owner_id, "title": title, "includeDraftIssues": include_draft_issues}}
    data = _graphql(owner, query, variables, token)
    return (data.get("copyProjectV2") or {}).get("projectV2") or {}


def list_fields(owner: str, number: int | str, token: Optional[str] = None) -> list[dict]:
    resolved = _resolved_token(owner, token)
    payload = _rest_request_owner("GET", owner, f"/projectsV2/{int(number)}/fields", resolved)
    items = payload if isinstance(payload, list) else payload.get("fields", []) if isinstance(payload, dict) else []
    return [_normalize_node_payload(item) for item in items]


def create_field(owner: str, number: int | str, name: str, data_type: str, *, options: Optional[list[str]] = None, token: Optional[str] = None) -> dict:
    resolved = _resolved_token(owner, token)
    body: dict[str, Any] = {"name": name, "data_type": data_type}
    if options:
        body["single_select_options"] = [{"name": option} for option in options]
    return _normalize_node_payload(_rest_request_owner("POST", owner, f"/projectsV2/{int(number)}/fields", resolved, json_payload=body))


def delete_field(owner: str, field_id: str, token: Optional[str] = None) -> dict:
    query = "mutation($input:DeleteProjectV2FieldInput!) { deleteProjectV2Field(input:$input) { deletedFieldId } }"
    data = _graphql(owner, query, {"input": {"fieldId": field_id}}, token)
    return {"deleted": True, "field_id": (data.get("deleteProjectV2Field") or {}).get("deletedFieldId", field_id)}


def list_items(owner: str, number: int | str, *, limit: int = 50, token: Optional[str] = None) -> list[dict]:
    resolved = _resolved_token(owner, token)
    payload = _rest_request_owner("GET", owner, f"/projectsV2/{int(number)}/items", resolved, params={"per_page": limit})
    items = payload if isinstance(payload, list) else payload.get("items", []) if isinstance(payload, dict) else []
    return [_normalize_node_payload(item) for item in items]


def add_item(owner: str, number: int | str, *, url: Optional[str] = None, content_id: Optional[str] = None, token: Optional[str] = None) -> dict:
    if not content_id and url:
        content_id = _content_id_from_url(url, _resolved_token(owner, token))
    if content_id:
        project_id = _project_id(owner, number, token)
        query = "mutation($input:AddProjectV2ItemByIdInput!) { addProjectV2ItemById(input:$input) { item { id } } }"
        data = _graphql(owner, query, {"input": {"projectId": project_id, "contentId": content_id}}, token)
        return (data.get("addProjectV2ItemById") or {}).get("item") or {}
    raise click.ClickException("Pass --url or --content-id.")


def _content_id_from_url(url: str, token: Optional[str]) -> str:
    parsed = urlparse(url)
    if parsed.netloc.lower() != "github.com":
        raise click.ClickException("--url must be a github.com issue or pull request URL.")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 4 or parts[2] not in {"issues", "pull"}:
        raise click.ClickException("--url must look like https://github.com/OWNER/REPO/issues/NUMBER or /pull/NUMBER.")
    owner, repo, kind, number = parts
    api_kind = "pulls" if kind == "pull" else "issues"
    payload = _rest_request("GET", f"/repos/{owner}/{repo}/{api_kind}/{number}", token)
    node_id = payload.get("node_id") if isinstance(payload, dict) else None
    if not node_id:
        raise click.ClickException(f"GitHub API response for {url} did not include node_id.")
    return str(node_id)


def create_draft_item(owner: str, number: int | str, title: str, *, body: Optional[str] = None, token: Optional[str] = None) -> dict:
    project_id = _project_id(owner, number, token)
    query = """
    mutation($input:AddProjectV2DraftIssueInput!) {
      addProjectV2DraftIssue(input:$input) { projectItem { id } }
    }
    """
    data = _graphql(owner, query, {"input": {"projectId": project_id, "title": title, "body": body or ""}}, token)
    return (data.get("addProjectV2DraftIssue") or {}).get("projectItem") or {}


def update_item_field(owner: str, number: int | str, item_id: str, field_id: str, value: dict, token: Optional[str] = None) -> dict:
    project_id = _project_id(owner, number, token)
    query = """
    mutation($input:UpdateProjectV2ItemFieldValueInput!) {
      updateProjectV2ItemFieldValue(input:$input) { projectV2Item { id } }
    }
    """
    data = _graphql(owner, query, {"input": {"projectId": project_id, "itemId": item_id, "fieldId": field_id, "value": value}}, token)
    payload: dict[str, Any] = (data.get("updateProjectV2ItemFieldValue") or {}).get("projectV2Item") or {"id": item_id}
    payload["field_id"] = field_id
    payload["value"] = value
    return payload


def clear_item_field(owner: str, number: int | str, item_id: str, field_id: str, token: Optional[str] = None) -> dict:
    project_id = _project_id(owner, number, token)
    query = "mutation($input:ClearProjectV2ItemFieldValueInput!) { clearProjectV2ItemFieldValue(input:$input) { projectV2Item { id } } }"
    data = _graphql(owner, query, {"input": {"projectId": project_id, "itemId": item_id, "fieldId": field_id}}, token)
    return (data.get("clearProjectV2ItemFieldValue") or {}).get("projectV2Item") or {"id": item_id}


def archive_item(owner: str, number: int | str, item_id: str, *, undo: bool = False, token: Optional[str] = None) -> dict:
    project_id = _project_id(owner, number, token)
    mutation = "unarchiveProjectV2Item" if undo else "archiveProjectV2Item"
    input_type = "UnarchiveProjectV2ItemInput" if undo else "ArchiveProjectV2ItemInput"
    query = f"mutation($input:{input_type}!) {{ {mutation}(input:$input) {{ item {{ id isArchived }} }} }}"
    data = _graphql(owner, query, {"input": {"projectId": project_id, "itemId": item_id}}, token)
    return (data.get(mutation) or {}).get("item") or {"id": item_id}


def delete_item(owner: str, number: int | str, item_id: str, token: Optional[str] = None) -> dict:
    project_id = _project_id(owner, number, token)
    query = "mutation($input:DeleteProjectV2ItemInput!) { deleteProjectV2Item(input:$input) { deletedItemId } }"
    data = _graphql(owner, query, {"input": {"projectId": project_id, "itemId": item_id}}, token)
    return {"deleted": True, "item_id": (data.get("deleteProjectV2Item") or {}).get("deletedItemId", item_id)}


def link_repository(owner: str, number: int | str, repository_id: str, token: Optional[str] = None) -> dict:
    return _link(owner, number, "linkProjectV2ToRepository", "LinkProjectV2ToRepositoryInput", "repositoryId", repository_id, "repository { id nameWithOwner url }", "repository", token)


def unlink_repository(owner: str, number: int | str, repository_id: str, token: Optional[str] = None) -> dict:
    return _link(owner, number, "unlinkProjectV2FromRepository", "UnlinkProjectV2FromRepositoryInput", "repositoryId", repository_id, "repository { id nameWithOwner url }", "repository", token)


def link_team(owner: str, number: int | str, team_id: str, token: Optional[str] = None) -> dict:
    return _link(owner, number, "linkProjectV2ToTeam", "LinkProjectV2ToTeamInput", "teamId", team_id, "team { id name slug }", "team", token)


def unlink_team(owner: str, number: int | str, team_id: str, token: Optional[str] = None) -> dict:
    return _link(owner, number, "unlinkProjectV2FromTeam", "UnlinkProjectV2FromTeamInput", "teamId", team_id, "team { id name slug }", "team", token)


def _link(owner: str, number: int | str, mutation: str, input_type: str, key: str, value: str, selection: str, payload_key: str, token: Optional[str]) -> dict:
    project_id = _project_id(owner, number, token)
    query = f"mutation($input:{input_type}!) {{ {mutation}(input:$input) {{ {selection} }} }}"
    data = _graphql(owner, query, {"input": {"projectId": project_id, key: value}}, token)
    return (data.get(mutation) or {}).get(payload_key) or {"id": value}


def mark_template(owner: str, number: int | str, *, undo: bool = False, token: Optional[str] = None) -> dict:
    project_id = _project_id(owner, number, token)
    mutation = "unmarkProjectV2AsTemplate" if undo else "markProjectV2AsTemplate"
    input_type = "UnmarkProjectV2AsTemplateInput" if undo else "MarkProjectV2AsTemplateInput"
    query = f"mutation($input:{input_type}!) {{ {mutation}(input:$input) {{ projectV2 {{ id number title template }} }} }}"
    data = _graphql(owner, query, {"input": {"projectId": project_id}}, token)
    return (data.get(mutation) or {}).get("projectV2") or {"id": project_id}

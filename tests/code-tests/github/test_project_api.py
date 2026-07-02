from chatgh.github import projects


def test_list_projects_filters_closed_and_normalizes_ids(monkeypatch):
    monkeypatch.setattr(projects, "_resolved_token", lambda owner, token: "token")
    monkeypatch.setattr(
        projects,
        "_rest_request_owner",
        lambda method, owner, suffix, token, **kwargs: [
            {"id": 1, "node_id": "PVT_open", "title": "Open", "state": "open"},
            {"id": 2, "node_id": "PVT_closed", "title": "Closed", "state": "closed"},
        ],
    )

    items = projects.list_projects("acme")

    assert items == [{"id": "PVT_open", "node_id": "PVT_open", "database_id": 1, "title": "Open", "state": "open"}]


def test_get_project_normalizes_rest_id_to_graphql_node_id(monkeypatch):
    monkeypatch.setattr(projects, "_resolved_token", lambda owner, token: "token")
    monkeypatch.setattr(
        projects,
        "_rest_request_owner",
        lambda method, owner, suffix, token, **kwargs: {"id": 1, "node_id": "PVT_project", "title": "Roadmap"},
    )

    project = projects.get_project("acme", 3)

    assert project == {"id": "PVT_project", "node_id": "PVT_project", "database_id": 1, "title": "Roadmap"}


def test_list_fields_normalizes_rest_id_to_graphql_node_id(monkeypatch):
    monkeypatch.setattr(projects, "_resolved_token", lambda owner, token: "token")
    monkeypatch.setattr(
        projects,
        "_rest_request_owner",
        lambda method, owner, suffix, token, **kwargs: [{"id": 123, "node_id": "PVTF_node", "name": "Status"}],
    )

    fields = projects.list_fields("acme", 3)

    assert fields == [{"id": "PVTF_node", "node_id": "PVTF_node", "database_id": 123, "name": "Status"}]


def test_list_items_normalizes_rest_id_to_graphql_node_id(monkeypatch):
    monkeypatch.setattr(projects, "_resolved_token", lambda owner, token: "token")
    monkeypatch.setattr(
        projects,
        "_rest_request_owner",
        lambda method, owner, suffix, token, **kwargs: [{"id": 456, "node_id": "PVTI_node", "content": {"title": "Do it"}}],
    )

    items = projects.list_items("acme", 3)

    assert items == [{"id": "PVTI_node", "node_id": "PVTI_node", "database_id": 456, "content": {"title": "Do it"}}]


def test_create_draft_item_uses_graphql_for_owner_independent_node_id(monkeypatch):
    captured = {}
    monkeypatch.setattr(projects, "_project_id", lambda owner, number, token: "PVT_project")

    def fake_graphql(owner, query, variables, token):
        captured.update({"owner": owner, "query": query, "variables": variables, "token": token})
        return {"addProjectV2DraftIssue": {"projectItem": {"id": "PVTI_draft"}}}

    monkeypatch.setattr(projects, "_graphql", fake_graphql)

    payload = projects.create_draft_item("acme", 3, "Draft", body="Body", token="tok")

    assert payload == {"id": "PVTI_draft"}
    assert "addProjectV2DraftIssue" in captured["query"]
    assert captured["variables"] == {"input": {"projectId": "PVT_project", "title": "Draft", "body": "Body"}}


def test_delete_field_avoids_union_field_selection(monkeypatch):
    captured = {}

    def fake_graphql(owner, query, variables, token):
        captured.update({"query": query, "variables": variables})
        return {"deleteProjectV2Field": {"clientMutationId": None}}

    monkeypatch.setattr(projects, "_graphql", fake_graphql)

    payload = projects.delete_field("acme", "PVTF_1")

    assert payload == {"deleted": True, "field_id": "PVTF_1"}
    assert "clientMutationId" in captured["query"]
    assert "projectV2Field" not in captured["query"]
    assert "deletedFieldId" not in captured["query"]


def test_link_repository_selects_repository_payload(monkeypatch):
    captured = {}
    monkeypatch.setattr(projects, "_project_id", lambda owner, number, token: "PVT_project")

    def fake_graphql(owner, query, variables, token):
        captured.update({"query": query, "variables": variables})
        return {"linkProjectV2ToRepository": {"repository": {"id": "R_1", "nameWithOwner": "acme/repo"}}}

    monkeypatch.setattr(projects, "_graphql", fake_graphql)

    payload = projects.link_repository("acme", 3, "R_1")

    assert payload == {"id": "R_1", "nameWithOwner": "acme/repo"}
    assert "repository" in captured["query"]
    assert "projectV2" not in captured["query"]

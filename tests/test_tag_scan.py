import httpx
import pytest
from fastapi.testclient import TestClient

import app
from spoolbud import dependencies as deps
from spoolbud.clients.spoolman import DuplicateTagUIDError, TagLookupError


def selected(client):
    return client.get("/status").json()["selected_spool_id"]


def matched_spool():
    return {
        "id": 42,
        "name": "Witchcraft PLA",
        "location": "F-008",
        "filament": {"vendor": {"name": "Cookiecad"}, "material": "PLA"},
        "extra": {"nfc_id": "04A2B3C4"},
    }


def test_tag_url_normalizes_uid_selects_spool_and_shows_shared_destinations(monkeypatch):
    async def lookup(uid):
        assert uid == "04A2B3C4"
        return matched_spool()

    monkeypatch.setattr(deps, "fetch_spool_by_tag_uid", lookup)
    with TestClient(app.app) as client:
        response = client.get("/tag/04:a2-b3:c4")
        assert response.status_code == 200
        assert selected(client) == 42
    assert "Spool 42 selected" in response.text
    assert "Cookiecad" in response.text
    assert "Witchcraft PLA" in response.text
    assert "Location: F-008" in response.text
    assert "Choose a destination" in response.text
    assert "Open bin scanner" in response.text
    assert "Moved" in response.text
    assert "Done" in response.text
    assert 'id="moveDestination"' in response.text
    assert 'data-spool-id="42"' in response.text


def test_same_tag_url_resolves_again_after_spoolman_reassignment(monkeypatch):
    state = {"spool": matched_spool(), "calls": 0}

    async def lookup(uid):
        state["calls"] += 1
        return state["spool"]

    monkeypatch.setattr(deps, "fetch_spool_by_tag_uid", lookup)
    with TestClient(app.app) as client:
        first = client.get("/tag/04A2B3C4")
        assert "Spool 42 selected" in first.text
        state["spool"] = {**matched_spool(), "id": 77, "name": "Reassigned spool"}
        second = client.get("/tag/04A2B3C4")
        assert "Spool 77 selected" in second.text
        assert selected(client) == 77
    assert state["calls"] == 2


def test_unknown_tag_clears_previous_selection_and_renders_help(monkeypatch):
    async def lookup(uid):
        assert uid == "04A2B3C4"
        return None

    async def spools():
        return [
            {"id": 42, "location": "F-008", "filament": {"vendor": {"name": "Cookiecad"}, "material": "PLA"}},
            {"id": 77, "name": "Backup PETG", "extra": {"nfc_id": "AABBCCDD"}},
        ]

    monkeypatch.setattr(deps, "fetch_spool_by_tag_uid", lookup)
    monkeypatch.setattr(deps, "fetch_spoolman_spools", spools)
    with TestClient(app.app) as client:
        client.get("/select/99", follow_redirects=False)
        response = client.get("/tag/04A2B3C4")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert selected(client) is None
    assert "Unassigned NFC Tag" in response.text
    assert "04A2B3C4" in response.text
    assert "Select the Spoolman spool" in response.text
    assert "Cookiecad" in response.text
    assert "Backup PETG" in response.text
    assert "Stored NFC ID reported by the Spoolman API" in response.text
    assert "Associate NFC tag" in response.text
    assert "Open Spoolman" in response.text
    assert "Try another tag" in response.text


def test_unassigned_page_treats_json_encoded_empty_nfc_fields_as_blank(monkeypatch):
    async def lookup(uid):
        return None

    async def spools():
        return [
            {"id": 42, "name": "Empty string", "extra": {"nfc_id": '""'}},
            {"id": 77, "name": "Encoded null", "extra": {"nfc_id": "null"}},
        ]

    monkeypatch.setattr(deps, "fetch_spool_by_tag_uid", lookup)
    monkeypatch.setattr(deps, "fetch_spoolman_spools", spools)
    with TestClient(app.app) as client:
        response = client.get("/tag/04A2B3C4")
    assert response.status_code == 200
    assert response.text.count("No NFC ID currently assigned.") == 2
    assert "confirmation will be required" not in response.text
    assert 'data-replace-existing="true"' not in response.text


def test_assignment_writes_normalized_uid_and_selects_spool(monkeypatch):
    calls = []

    async def associate(spool_id, uid, *, replace_existing=False):
        calls.append((spool_id, uid, replace_existing))
        return {"id": spool_id, "extra": {"nfc_id": uid}}

    monkeypatch.setattr(deps, "associate_spool_with_tag_uid", associate)
    with TestClient(app.app) as client:
        response = client.post(
            "/tag/04:a2-b3:c4/assign",
            json={"spool_id": 42, "replace_existing": False},
        )
        assert response.status_code == 200
        assert response.json() == {"assigned_spool_id": 42, "uid": "04A2B3C4"}
        assert response.headers["cache-control"] == "no-store"
        assert selected(client) == 42
    assert calls == [(42, "04A2B3C4", False)]


def test_first_tap_assignment_then_resolves_to_selected_workflow(monkeypatch):
    state = {"assigned": False}

    async def lookup(uid):
        return matched_spool() if state["assigned"] else None

    async def spools():
        return [matched_spool() | {"extra": {}}]

    async def associate(spool_id, uid, *, replace_existing=False):
        state["assigned"] = True
        return matched_spool()

    monkeypatch.setattr(deps, "fetch_spool_by_tag_uid", lookup)
    monkeypatch.setattr(deps, "fetch_spoolman_spools", spools)
    monkeypatch.setattr(deps, "associate_spool_with_tag_uid", associate)
    with TestClient(app.app) as client:
        first_tap = client.get("/tag/04A2B3C4")
        assert "Unassigned NFC Tag" in first_tap.text
        assert selected(client) is None
        assert client.post("/tag/04A2B3C4/assign", json={"spool_id": 42}).status_code == 200
        resolved = client.get("/tag/04A2B3C4")
        assert "Spool 42 selected" in resolved.text
        assert selected(client) == 42


def test_assignment_forwards_explicit_replacement_confirmation(monkeypatch):
    async def associate(spool_id, uid, *, replace_existing=False):
        assert replace_existing is True
        return {"id": spool_id, "extra": {"nfc_id": uid}}

    monkeypatch.setattr(deps, "associate_spool_with_tag_uid", associate)
    with TestClient(app.app) as client:
        response = client.post("/tag/04A2B3C4/assign", json={"spool_id": 77, "replace_existing": True})
    assert response.status_code == 200


def test_assignment_failure_is_actionable_and_clears_selection(monkeypatch):
    async def associate(spool_id, uid, *, replace_existing=False):
        raise TagLookupError(409, "The selected spool already has a different NFC ID.")

    monkeypatch.setattr(deps, "associate_spool_with_tag_uid", associate)
    with TestClient(app.app) as client:
        client.get("/select/99", follow_redirects=False)
        response = client.post("/tag/04A2B3C4/assign", json={"spool_id": 42})
        assert response.status_code == 409
        assert "different NFC ID" in response.json()["detail"]
        assert selected(client) is None


@pytest.mark.parametrize(
    "body",
    [{}, {"spool_id": 0}, {"spool_id": True}, {"spool_id": 42, "unexpected": True}],
)
def test_invalid_assignment_never_writes_and_clears_selection(monkeypatch, body):
    async def unexpected_associate(spool_id, uid, *, replace_existing=False):
        pytest.fail("Invalid assignments must not reach Spoolman")

    monkeypatch.setattr(deps, "associate_spool_with_tag_uid", unexpected_associate)
    with TestClient(app.app) as client:
        client.get("/select/99", follow_redirects=False)
        response = client.post("/tag/04A2B3C4/assign", json=body)
        assert response.status_code == 400
        assert selected(client) is None


def test_invalid_tag_never_calls_spoolman_and_clears_selection(monkeypatch):
    async def unexpected_lookup(uid):
        pytest.fail("Invalid UIDs must not reach Spoolman")

    monkeypatch.setattr(deps, "fetch_spool_by_tag_uid", unexpected_lookup)
    with TestClient(app.app) as client:
        client.get("/select/99", follow_redirects=False)
        response = client.get("/tag/04A2ZZ")
        assert response.status_code == 400
        assert selected(client) is None
    assert "Invalid NFC Tag" in response.text


def test_invalid_tag_page_escapes_user_input(monkeypatch):
    async def unexpected_lookup(uid):
        pytest.fail("Invalid UIDs must not reach Spoolman")

    monkeypatch.setattr(deps, "fetch_spool_by_tag_uid", unexpected_lookup)
    with TestClient(app.app) as client:
        response = client.get("/tag/%3Cimg%20src=x%20onerror=alert(1)%3E")
    assert response.status_code == 400
    assert "<img src=x" not in response.text
    assert "&lt;img src=x" in response.text


def test_duplicate_uid_is_configuration_error_and_logs_spool_ids(monkeypatch, caplog):
    async def lookup(uid):
        raise DuplicateTagUIDError([42, 77])

    monkeypatch.setattr(deps, "fetch_spool_by_tag_uid", lookup)
    with TestClient(app.app) as client:
        response = client.get("/tag/04A2B3C4")
        assert response.status_code == 409
        assert selected(client) is None
    assert "NFC configuration error" in response.text
    assert "Spoolman's API reports this NFC ID on multiple spools" in response.text
    assert "Affected spool records" in response.text
    assert ">42</a>" in response.text
    assert ">77</a>" in response.text
    assert "42, 77" in caplog.text


def test_spoolman_failure_is_actionable_and_clears_selection(monkeypatch):
    async def lookup(uid):
        raise TagLookupError(502, "Could not reach Spoolman. Check its connection, then try again.")

    monkeypatch.setattr(deps, "fetch_spool_by_tag_uid", lookup)
    with TestClient(app.app) as client:
        client.get("/select/99", follow_redirects=False)
        response = client.get("/tag/04A2B3C4")
        assert response.status_code == 502
        assert selected(client) is None
    assert "Could not check NFC tag" in response.text
    assert "Check its connection" in response.text


def test_api_scan_uses_compatibility_resolver_and_normalizes_uid(monkeypatch):
    async def lookup(uid):
        assert uid == "04A2B3C4"
        return matched_spool()

    monkeypatch.setattr(deps, "fetch_spool_by_tag_uid", lookup)
    with TestClient(app.app) as client:
        response = client.post("/api/tag/scan", json={"uid": "04:a2-b3:c4", "reader_id": "desk-1"})
        assert response.json() == {"matched_spool_id": 42}
        assert selected(client) == 42


@pytest.mark.parametrize("body", [{}, [], {"uid": ""}, {"uid": 42}, {"uid": "04A2?B3"}, {"uid": "AA", "spool_id": 42}])
def test_invalid_api_scan_clears_selection_without_lookup(monkeypatch, body):
    async def unexpected_lookup(uid):
        pytest.fail("Invalid API scans must not reach Spoolman")

    monkeypatch.setattr(deps, "fetch_spool_by_tag_uid", unexpected_lookup)
    with TestClient(app.app) as client:
        client.get("/select/99", follow_redirects=False)
        assert client.post("/api/tag/scan", json=body).status_code == 400
        assert selected(client) is None


def test_tag_selected_spool_moves_through_existing_location_workflow(monkeypatch):
    moves = []

    async def lookup(uid):
        return matched_spool()

    async def patch(spool_id, location):
        moves.append((spool_id, location))
        return httpx.Response(200, request=httpx.Request("PATCH", "https://spoolman.test"))

    monkeypatch.setattr(deps, "fetch_spool_by_tag_uid", lookup)
    monkeypatch.setattr(deps, "patch_spool_location", patch)
    with TestClient(app.app) as client:
        client.get("/tag/04A2B3C4")
        response = client.post("/api/move", json={"spool_id": 42, "location": "f-012"})
        assert response.json() == {"spool_id": 42, "location": "F-012"}
        assert selected(client) is None
    assert moves == [(42, "F-012")]


def test_home_explains_iphone_url_flow_without_browser_nfc_api():
    with TestClient(app.app) as client:
        home = client.get("/").text
        spools = client.get("/spools").text
    assert "/tag/04A2B3C4D5E6F7" in home
    assert "does not use Web NFC" in home
    assert "NDEFReader" not in home
    assert "readNfc" not in home
    assert "extra field" in spools
    assert "/tag/&lt;uid&gt;" in spools

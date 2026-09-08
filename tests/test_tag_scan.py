import json

import httpx
import pytest
from fastapi.testclient import TestClient

import app
import spoolman_tags


@pytest.fixture
def upstream(monkeypatch):
    state = {"response": httpx.Response(200, json={"matched_spool_id": 42}), "requests": []}
    real_client = httpx.AsyncClient

    def handle(request):
        state["requests"].append(request)
        assert request.method == "POST"
        assert request.url.path == "/api/v1/tag/scan"
        if isinstance(state["response"], Exception):
            raise state["response"]
        return state["response"]

    monkeypatch.setattr(spoolman_tags.httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    monkeypatch.setattr(app, "SPOOLMAN_BASE", "https://spoolman.test")
    return state


def selected(client):
    return client.get("/status").json()["selected_spool_id"]


def test_tag_scan_forwards_contract_and_uses_only_upstream_match(upstream, monkeypatch):
    monkeypatch.setattr(app, "API_TOKEN", "test-credential")
    upstream["response"] = httpx.Response(200, json={"uid": "04A2B3C4", "matched_spool_id": 42, "spool": {"id": 999}})
    body = {"uid": "04:a2-b3:c4", "reader_id": "desk-1", "name": "Desk", "format": "ntag", "payload_b64": "NDI="}
    with TestClient(app.app) as client:
        response = client.post("/api/tag/scan", json=body)
        assert response.json() == {"matched_spool_id": 42}
        assert selected(client) == 42
    assert len(upstream["requests"]) == 1
    request = upstream["requests"][0]
    assert json.loads(request.content) == body
    assert request.headers["authorization"] == "Bearer test-credential"
    assert "test-credential" not in response.text


def test_unknown_numeric_uid_does_not_fall_back_to_spool_id(upstream):
    upstream["response"] = httpx.Response(200, json={"matched_spool_id": None, "spool": {"id": 99}})
    with TestClient(app.app) as client:
        client.get("/select/99", follow_redirects=False)
        response = client.post("/api/tag/scan", json={"uid": "42"})
        assert response.status_code == 200
        assert response.json()["matched_spool_id"] is None
        assert "Link it in Spoolman" in response.text
        assert selected(client) is None
    assert json.loads(upstream["requests"][0].content) == {"uid": "42"}


def test_repeated_scans_resolve_again_after_upstream_reassignment(upstream):
    with TestClient(app.app) as client:
        assert client.post("/api/tag/scan", json={"uid": "04AABB"}).json()["matched_spool_id"] == 42
        upstream["response"] = httpx.Response(200, json={"matched_spool_id": 77})
        assert client.post("/api/tag/scan", json={"uid": "04AABB"}).json()["matched_spool_id"] == 77
        assert selected(client) == 77
    assert len(upstream["requests"]) == 2


@pytest.mark.parametrize("result", [{}, {"spool": {"id": 42}}, [], {"matched_spool_id": "42"},
                                         {"matched_spool_id": True}, {"matched_spool_id": 42.0},
                                         {"matched_spool_id": 0}, {"matched_spool_id": -1}])
def test_invalid_match_response_clears_previous_selection(upstream, result):
    upstream["response"] = httpx.Response(200, json=result)
    with TestClient(app.app) as client:
        client.get("/select/99", follow_redirects=False)
        response = client.post("/api/tag/scan", json={"uid": "04AABB"})
        assert response.status_code == 502
        assert selected(client) is None


@pytest.mark.parametrize("status, expected, message", [
    (400, 400, "rejected the scan"), (422, 400, "rejected the scan"),
    (401, 502, "credentials"), (403, 502, "credentials"),
    (404, 502, "0.27+"), (405, 502, "0.27+"), (501, 502, "0.27+"),
    (429, 502, "service is available"), (500, 502, "service is available"),
    (302, 502, "service is available"),
])
def test_upstream_errors_are_actionable_and_never_expose_body(upstream, status, expected, message):
    upstream["response"] = httpx.Response(status, text="secret-upstream-details", headers={"location": "https://other.test"})
    with TestClient(app.app) as client:
        client.get("/select/99", follow_redirects=False)
        response = client.post("/api/tag/scan", json={"uid": "04AABB"})
        assert response.status_code == expected
        assert message in response.text
        assert "secret-upstream-details" not in response.text
        assert selected(client) is None
        # An unavailable tag API must not disable legacy selection.
        assert client.get("/scan?value=42", follow_redirects=False).status_code == 302
        assert selected(client) == 42
    assert len(upstream["requests"]) == 1  # No redirect or retry.


@pytest.mark.parametrize("failure", [httpx.ConnectError("secret"), httpx.ReadTimeout("secret"),
                                      httpx.Response(200, text="not JSON secret")])
def test_transport_or_json_failure_clears_selection(upstream, failure):
    upstream["response"] = failure
    with TestClient(app.app) as client:
        client.get("/select/99", follow_redirects=False)
        response = client.post("/api/tag/scan", json={"uid": "04AABB"})
        assert response.status_code == 502
        assert "secret" not in response.text
        assert selected(client) is None


@pytest.mark.parametrize("body", [{}, [], {"uid": ""}, {"uid": 42}, {"uid": "A" * 129},
                                  {"uid": "AA", "reader_id": "has spaces"},
                                  {"uid": "AA", "payload_b64": "x" * 8193},
                                  {"uid": "AA", "matched_spool_id": 42},
                                  {"uid": "AA", "spool_id": 42}])
def test_invalid_client_scan_clears_selection_without_upstream_call(upstream, body):
    with TestClient(app.app) as client:
        client.get("/select/99", follow_redirects=False)
        assert client.post("/api/tag/scan", json=body).status_code == 400
        assert selected(client) is None
    assert not upstream["requests"]


@pytest.mark.parametrize("content, content_type", [("{bad", "application/json"), ('{"uid":"AA"}', "text/plain")])
def test_malformed_json_or_wrong_content_type_clears_selection(upstream, content, content_type):
    with TestClient(app.app) as client:
        client.get("/select/99", follow_redirects=False)
        assert client.post("/api/tag/scan", content=content, headers={"content-type": content_type}).status_code == 400
        assert selected(client) is None
    assert not upstream["requests"]


def test_device_scan_does_not_select_an_unrelated_browser(upstream):
    with TestClient(app.app) as browser, TestClient(app.app) as device:
        browser.get("/select/99", follow_redirects=False)
        device.post("/api/tag/scan", json={"uid": "AA", "reader_id": "printer-1"})
        assert selected(device) == 42
        assert selected(browser) == 99

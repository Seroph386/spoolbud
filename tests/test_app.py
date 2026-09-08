import httpx
import pytest
from fastapi.testclient import TestClient

import app as spoolbud_app
from spoolbud import dependencies as deps


def create_client() -> TestClient:
    return TestClient(spoolbud_app.app)


def test_extract_spool_id_variants():
    assert spoolbud_app.extract_spool_id("web+spoolman:s-42") == 42
    assert spoolbud_app.extract_spool_id("https://filament.igetno.net/spool/show/42") == 42
    assert spoolbud_app.extract_spool_id("https://filament.igetno.net/spool/42") == 42
    assert spoolbud_app.extract_spool_id("https://x.test/thing?spool_id=7") == 7
    assert spoolbud_app.extract_spool_id("123") == 123
    assert spoolbud_app.extract_spool_id("nope") is None


def test_scan_sets_cookie_and_redirects():
    with create_client() as client:
        resp = client.get("/scan", params={"value": "https://filament.igetno.net/spool/42"}, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"].endswith("/spool/show/42")
    assert spoolbud_app.COOKIE_NAME in resp.headers.get("set-cookie", "")


def test_scan_stay_sets_cookie_and_shows_scanner_page(monkeypatch):
    async def fake_fetch(spool_id: int):
        assert spool_id == 42
        return {"id": 42, "name": "Orange PETG"}

    monkeypatch.setattr(deps, "fetch_spoolman_spool", fake_fetch)

    with create_client() as client:
        resp = client.get(
            "/scan",
            params={"value": "web+spoolman:s-42", "stay": "1"},
            follow_redirects=False,
        )
    assert resp.status_code == 200
    assert "Spool 42 selected" in resp.text
    assert "Orange PETG" in resp.text
    assert "Open bin scanner" in resp.text
    assert "scannerVideo" in resp.text
    assert "scannerCanvas" in resp.text
    assert "Compatibility scanner is active for this browser." in resp.text
    assert spoolbud_app.COOKIE_NAME in resp.headers.get("set-cookie", "")


def test_scan_stay_survives_spoolman_lookup_failure(monkeypatch):
    async def fake_fetch(spool_id: int):
        assert spool_id == 42
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(deps, "fetch_spoolman_spool", fake_fetch)

    with create_client() as client:
        resp = client.get(
            "/scan",
            params={"value": "https://filament.igetno.net/spool/42", "stay": "1"},
            follow_redirects=False,
        )

    assert resp.status_code == 200
    assert "Spool 42 selected" in resp.text
    assert "could not load its details from Spoolman right now" in resp.text


def test_home_page_exposes_spool_scanner():
    with create_client() as client:
        resp = client.get("/")

    assert resp.status_code == 200
    assert "Scan a Spoolman QR" in resp.text
    assert "startSpoolScanner" in resp.text
    assert "spoolScannerVideo" in resp.text
    assert "web+spoolman:s-42" in resp.text


def test_healthz_contract_is_stable():
    with create_client() as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "spoolman_base": spoolbud_app.SPOOLMAN_BASE}


def test_bin_without_cookie_shows_bin_contents(monkeypatch):
    async def fake_fetch(location: str):
        assert location == "F-001"
        return [
            {
                "id": 42,
                "filament": {
                    "vendor": {"name": "Prusament"},
                    "material": "PLA",
                    "color_hex": "#112233",
                },
            }
        ]

    monkeypatch.setattr(deps, "fetch_spools_in_location", fake_fetch)

    with create_client() as client:
        resp = client.get("/bin/F-001")
    assert resp.status_code == 200
    assert "Contents of F-001" in resp.text
    assert "Spool 42" in resp.text
    assert "Color #112233" in resp.text
    assert 'style="background:#112233;' in resp.text


def test_bin_without_cookie_shows_empty_bin(monkeypatch):
    async def fake_fetch(location: str):
        assert location == "F-001"
        return []

    monkeypatch.setattr(deps, "fetch_spools_in_location", fake_fetch)

    with create_client() as client:
        resp = client.get("/bin/F-001")
    assert resp.status_code == 200
    assert "F-001 is empty" in resp.text


def test_bin_with_cookie_updates_location_and_clears_cookie(monkeypatch):
    async def fake_patch(spool_id: int, location: str):
        assert spool_id == 42
        assert location == "F-001"
        return httpx.Response(200, request=httpx.Request("PATCH", "https://spoolman.test"))

    monkeypatch.setattr(deps, "patch_spool_location", fake_patch)

    with create_client() as client:
        client.cookies.set(spoolbud_app.COOKIE_NAME, "42")
        resp = client.get("/bin/F-001", follow_redirects=False)

    assert resp.status_code == 302
    assert resp.headers["location"].endswith("/spool/show/42")
    set_cookie = resp.headers.get("set-cookie", "")
    assert spoolbud_app.COOKIE_NAME in set_cookie
    assert "Max-Age=0" in set_cookie or "expires=" in set_cookie.lower()


def test_status_reads_cookie():
    with create_client() as client:
        client.cookies.set(spoolbud_app.COOKIE_NAME, "42")
        resp = client.get("/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["selected_spool_id"] == 42
    assert body["selected_spool_url"].endswith("/spool/show/42")


def test_api_bins_default():
    with create_client() as client:
        resp = client.get("/api/bins")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["source"] == "default"
    assert "F-001" in payload["bins"]
    assert "B-004" in payload["bins"]


def test_api_spools(monkeypatch):
    async def fake_fetch():
        return [{"id": 9}, {"id": 1}, {"id": 9}, {"id": "bad"}]

    monkeypatch.setattr(deps, "fetch_spoolman_spools", fake_fetch)

    with create_client() as client:
        resp = client.get("/api/spools")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["source"] == "spoolman"
    assert payload["spool_ids"] == [1, 9]


def test_qr_svg_endpoint():
    with create_client() as client:
        resp = client.get("/qr.svg", params={"value": "https://spoolbud.example.net/bin/F-001"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in resp.content


def test_bins_page_renders():
    with create_client() as client:
        resp = client.get("/bins")
    assert resp.status_code == 200
    assert "Bin QR Generator" in resp.text
    assert "themeToggle" in resp.text
    assert "loadDefault" in resp.text
    assert "loadSpoolman" in resp.text


def test_spools_page_renders():
    with create_client() as client:
        resp = client.get("/spools")
    assert resp.status_code == 200
    assert "Spoolman-Compatible Spool QR Labels" in resp.text
    assert "loadSpoolmanSpools" in resp.text
    assert "includeStayFlag" in resp.text
    assert "Full SpoolBud /scan URL" in resp.text
    assert "renderSpools" in resp.text


@pytest.mark.parametrize("via_api", [True, False])
def test_move_stays_in_spoolbud_and_clears_selection(monkeypatch, via_api):
    async def fake_patch(spool_id, location):
        assert (spool_id, location) == (42, "PRINTER / LEFT & <RIGHT>")
        return httpx.Response(200, request=httpx.Request("PATCH", "https://spoolman.test"))

    monkeypatch.setattr(deps, "patch_spool_location", fake_patch)
    with create_client() as client:
        client.get("/select/42", follow_redirects=False)
        if via_api:
            response = client.post("/api/move", json={"spool_id": 42, "location": " printer / left & <right> "})
            assert response.json() == {"spool_id": 42, "location": "PRINTER / LEFT & <RIGHT>"}
        else:
            response = client.get("/bin/printer%20%2F%20left%20%26%20%3Cright%3E?stay=1")
            assert "Spool 42 moved to PRINTER / LEFT &amp; &lt;RIGHT&gt;" in response.text
            assert "Move another spool" in response.text
        assert response.status_code == 200
        assert client.get("/status").json()["selected_spool_id"] is None


@pytest.mark.parametrize("via_api", [True, False])
@pytest.mark.parametrize("failure", ["timeout", "http"])
def test_failed_move_preserves_selection_without_exposing_upstream_details(monkeypatch, via_api, failure):
    async def fake_patch(spool_id, location):
        if failure == "timeout":
            raise httpx.TimeoutException("private connection details")
        return httpx.Response(500, text="private connection details", request=httpx.Request("PATCH", "https://spoolman.test"))

    monkeypatch.setattr(deps, "patch_spool_location", fake_patch)
    with create_client() as client:
        client.get("/select/42", follow_redirects=False)
        response = (client.post("/api/move", json={"spool_id": 42, "location": "F-001"}) if via_api
                    else client.get("/bin/F-001?stay=1"))
        assert response.status_code == 502
        assert "could not confirm the move" in response.text
        assert "private connection details" not in response.text
        assert client.get("/status").json()["selected_spool_id"] == 42


@pytest.mark.parametrize("selection", [None, 99])
@pytest.mark.parametrize("action", ["move", "cancel", "qr"])
def test_stale_page_cannot_move_or_clear_another_selection(monkeypatch, selection, action):
    async def unexpected_patch(*args):
        pytest.fail("A stale page must never update Spoolman")

    monkeypatch.setattr(deps, "patch_spool_location", unexpected_patch)
    with create_client() as client:
        if selection:
            client.get(f"/select/{selection}", follow_redirects=False)
        if action == "qr":
            response = client.get("/bin/F-001?spool_id=42&stay=1")
        else:
            endpoint = "/api/move" if action == "move" else "/api/selection/clear"
            response = client.post(endpoint, json={"spool_id": 42, "location": "F-001"})
        assert response.status_code == 409
        assert client.get("/status").json()["selected_spool_id"] == selection


def test_cancel_selection():
    with create_client() as client:
        client.get("/select/42", follow_redirects=False)
        assert client.post("/api/selection/clear", json={"spool_id": 42}).status_code == 200
        assert client.get("/status").json()["selected_spool_id"] is None


@pytest.mark.parametrize("location", ["  ", "x" * 201])
def test_invalid_destination_never_calls_spoolman(monkeypatch, location):
    async def unexpected_patch(*args):
        pytest.fail("Invalid locations must never reach Spoolman")

    monkeypatch.setattr(deps, "patch_spool_location", unexpected_patch)
    with create_client() as client:
        client.get("/select/42", follow_redirects=False)
        assert client.post("/api/move", json={"spool_id": 42, "location": location}).status_code == 400
        assert client.get("/status").json()["selected_spool_id"] == 42


def test_destinations_merge_configured_empty_bins_and_spoolman(monkeypatch):
    monkeypatch.setattr(deps, "DESTINATIONS", " empty-bin, printer / left\nEMPTY-BIN ")

    async def fake_fetch():
        return [{"id": 42, "location": "printer / left"}, {"id": 43, "location": "used-bin"}]

    monkeypatch.setattr(deps, "fetch_spoolman_spools", fake_fetch)
    with create_client() as client:
        response = client.get("/api/bins?source=all")
    assert response.json() == {"source": "all", "bins": ["EMPTY-BIN", "PRINTER / LEFT", "USED-BIN"], "warning": None}


@pytest.mark.parametrize("configured", ["", " empty-bin "])
def test_destination_lookup_failure_keeps_fallback_visible(monkeypatch, configured):
    monkeypatch.setattr(deps, "DESTINATIONS", configured)

    async def failed_fetch():
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(deps, "fetch_spoolman_spools", failed_fetch)
    with create_client() as client:
        response = client.get("/api/bins?source=all")
    assert response.status_code == 200
    assert response.json()["bins"] == (["EMPTY-BIN"] if configured else sorted(spoolbud_app.default_bins()))
    assert response.json()["warning"]


@pytest.mark.parametrize("color", ["#112233", "112233"])
def test_spool_preparation_details_and_selected_page_escape_content(monkeypatch, color):
    spool = {"id": 42, "name": '<img src=x onerror="alert(1)">', "location": "F-001",
             "filament": {"vendor": {"name": "Test vendor"}, "material": "PETG", "color_hex": color}}

    async def fake_fetch_all():
        return [spool]

    async def fake_fetch_one(spool_id):
        return spool

    monkeypatch.setattr(deps, "fetch_spoolman_spools", fake_fetch_all)
    monkeypatch.setattr(deps, "fetch_spoolman_spool", fake_fetch_one)
    with create_client() as client:
        data = client.get("/api/spools").json()
        response = client.get("/scan?value=42&stay=1")
    assert data["spool_ids"] == [42]
    assert data["spools"][0]["color_hex"] == "#112233"
    assert data["spools"][0]["locations"] == ["F-001"]
    assert "Test vendor / PETG" in data["spools"][0]["description"]
    assert spool["name"] not in response.text
    assert "&lt;img" in response.text
    assert "Choose a destination" in response.text
    assert 'data-spool-id="42"' in response.text
    assert "Location: F-001" in response.text

from fastapi.testclient import TestClient

import app as spoolbud_app


def create_client() -> TestClient:
    return TestClient(spoolbud_app.app)


def test_extract_spool_id_variants():
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


def test_scan_stay_sets_cookie_and_shows_scanner_page():
    with create_client() as client:
        resp = client.get(
            "/scan",
            params={"value": "https://filament.igetno.net/spool/42", "stay": "1"},
            follow_redirects=False,
        )
    assert resp.status_code == 200
    assert "Spool 42 selected" in resp.text
    assert "Scan bin QR" in resp.text
    assert "scannerVideo" in resp.text
    assert spoolbud_app.COOKIE_NAME in resp.headers.get("set-cookie", "")


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

    monkeypatch.setattr(spoolbud_app, "fetch_spools_in_location", fake_fetch)

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

    monkeypatch.setattr(spoolbud_app, "fetch_spools_in_location", fake_fetch)

    with create_client() as client:
        resp = client.get("/bin/F-001")
    assert resp.status_code == 200
    assert "F-001 is empty" in resp.text


def test_bin_with_cookie_updates_location_and_clears_cookie(monkeypatch):
    class FakeResponse:
        status_code = 200
        text = ""

    async def fake_patch(spool_id: int, location: str):
        assert spool_id == 42
        assert location == "F-001"
        return FakeResponse()

    monkeypatch.setattr(spoolbud_app, "patch_spool_location", fake_patch)

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
    assert "web+spoolman:s-" in resp.text
    assert "renderSpools" in resp.text

from fastapi.testclient import TestClient

import app as spoolbud_app

client = TestClient(spoolbud_app.app)


def test_extract_spool_id_variants():
    assert spoolbud_app.extract_spool_id("https://filament.igetno.net/spool/42") == 42
    assert spoolbud_app.extract_spool_id("https://x.test/thing?spool_id=7") == 7
    assert spoolbud_app.extract_spool_id("123") == 123
    assert spoolbud_app.extract_spool_id("nope") is None


def test_scan_sets_cookie_and_redirects():
    resp = client.get("/scan", params={"value": "https://filament.igetno.net/spool/42"}, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"].endswith("/spool/42")
    assert spoolbud_app.COOKIE_NAME in resp.headers.get("set-cookie", "")


def test_bin_without_cookie_errors():
    resp = client.get("/bin/F-001")
    assert resp.status_code == 400
    assert "No active spool selected" in resp.text


def test_status_reads_cookie():
    resp = client.get("/status", cookies={spoolbud_app.COOKIE_NAME: "42"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["selected_spool_id"] == 42
    assert body["selected_spool_url"].endswith("/spool/42")


def test_api_bins_default():
    resp = client.get("/api/bins")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["source"] == "default"
    assert "F-001" in payload["bins"]
    assert "B-004" in payload["bins"]


def test_qr_svg_endpoint():
    resp = client.get("/qr.svg", params={"value": "https://spoolbud.example.net/bin/F-001"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in resp.content


def test_bins_page_renders():
    resp = client.get("/bins")
    assert resp.status_code == 200
    assert "Bin QR Generator" in resp.text

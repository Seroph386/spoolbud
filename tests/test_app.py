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

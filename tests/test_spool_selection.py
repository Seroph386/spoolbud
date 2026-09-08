from types import SimpleNamespace

from starlette.responses import Response

from spoolbud.services.spool_selection import clear_selected_spool, get_selected_spool, set_selected_spool


def test_get_selected_spool_reads_valid_cookie():
    request = SimpleNamespace(cookies={"selection": "42"})
    assert get_selected_spool(request, cookie_name="selection") == 42


def test_get_selected_spool_rejects_invalid_cookie():
    request = SimpleNamespace(cookies={"selection": "invalid"})
    assert get_selected_spool(request, cookie_name="selection") is None


def test_set_selected_spool_preserves_cookie_contract():
    response = set_selected_spool(Response(), 42, cookie_name="selection", max_age=123)
    header = response.headers["set-cookie"]
    assert "selection=42" in header
    assert "Max-Age=123" in header
    assert "SameSite=Lax" in header


def test_clear_selected_spool_expires_cookie():
    response = clear_selected_spool(Response(), cookie_name="selection")
    header = response.headers["set-cookie"]
    assert "selection=" in header
    assert "Max-Age=0" in header

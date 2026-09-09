import asyncio
import json

import httpx
import pytest

from spoolbud.clients.spoolman import DuplicateTagUIDError, SpoolmanClient, TagAssignmentError, TagLookupError


def client_for(handler, *, token="secret"):
    transport = httpx.MockTransport(handler)
    return SpoolmanClient(
        "https://spoolman.test/",
        token,
        client_factory=lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs),
    )


def test_get_spool():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/api/v1/spool/42"
        assert request.headers["authorization"] == "Bearer secret"
        return httpx.Response(200, json={"id": 42})

    assert asyncio.run(client_for(handler).get_spool(42)) == {"id": 42}


def test_get_spools():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/api/v1/spool"
        return httpx.Response(200, json=[{"id": 1}, {"id": 2}])

    assert asyncio.run(client_for(handler).get_spools()) == [{"id": 1}, {"id": 2}]


def test_update_spool_location():
    def handler(request):
        assert request.method == "PATCH"
        assert request.url.path == "/api/v1/spool/42"
        assert request.read() == b'{"location":"F-001"}'
        return httpx.Response(200, json={"id": 42, "location": "F-001"})

    response = asyncio.run(client_for(handler).update_spool_location(42, "F-001"))
    assert response.status_code == 200


@pytest.mark.parametrize("method", ["get_spool", "get_spools"])
def test_lookup_propagates_non_success(method):
    client = client_for(lambda request: httpx.Response(503))
    operation = client.get_spool(42) if method == "get_spool" else client.get_spools()
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(operation)


def test_connection_failure_propagates():
    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    with pytest.raises(httpx.ConnectError):
        asyncio.run(client_for(handler).get_spools())


def test_legacy_tag_lookup_uses_safe_extra_filter_and_validates_matches():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["authorization"] == "Bearer secret"
        if request.url.path == "/api/v1/info":
            return httpx.Response(200, json={"version": "0.26.0"})
        assert request.url.path == "/api/v1/spool"
        assert dict(request.url.params) == {"extra.nfc_id": "04A2B3C4"}
        return httpx.Response(
            200,
            json=[
                {"id": 77, "extra": {"nfc_id": "04A2B3C4FF"}},
                {"id": 42, "extra": {"nfc_id": "04:a2:b3:c4"}},
                {"id": 88, "extra": {"nfc_id": "malformed?"}},
                {"id": 99, "extra": {"nfc_id": 1234}},
            ],
        )

    spool = asyncio.run(client_for(handler).get_spool_by_tag_uid("04-A2-B3-C4"))
    assert spool == {"id": 42, "extra": {"nfc_id": "04:a2:b3:c4"}}
    assert len(requests) == 2


def test_invalid_uid_never_reaches_spoolman_query_construction():
    def handler(request):
        pytest.fail("Invalid UID must not produce an upstream request")

    with pytest.raises(ValueError):
        asyncio.run(client_for(handler).get_spool_by_tag_uid("04A2&tag=anything"))


def test_legacy_tag_lookup_returns_none_for_no_valid_match_or_malformed_extra():
    def handler(request):
        if request.url.path == "/api/v1/info":
            return httpx.Response(200, json={"version": "0.26.0"})
        return httpx.Response(200, json=[{"id": 42, "extra": {"nfc_id": "not-a-uid"}}, {"id": 77}])

    assert asyncio.run(client_for(handler).get_spool_by_tag_uid("04A2B3C4")) is None


def test_legacy_tag_lookup_rejects_duplicate_normalized_uids():
    def handler(request):
        if request.url.path == "/api/v1/info":
            return httpx.Response(200, json={"version": "0.26.0"})
        return httpx.Response(
            200,
            json=[
                {"id": 42, "extra": {"nfc_id": "04A2B3C4"}},
                {"id": 77, "extra": {"nfc_id": "04-A2-B3-C4"}},
            ],
        )

    with pytest.raises(DuplicateTagUIDError) as exc_info:
        asyncio.run(client_for(handler).get_spool_by_tag_uid("04A2B3C4"))
    assert exc_info.value.spool_ids == [42, 77]


def test_server_advertised_native_lookup_is_preferred():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/api/v1/info":
            return httpx.Response(200, json={"version": "v0.27.0"})
        assert dict(request.url.params) == {"tag": "04A2B3C4"}
        return httpx.Response(200, json=[{"id": 42, "tags": [{"uid": "04A2B3C4"}]}])

    spool = asyncio.run(client_for(handler).get_spool_by_tag_uid("04A2B3C4"))
    assert spool["id"] == 42
    assert len(requests) == 2


@pytest.mark.parametrize("native_response", [httpx.Response(404), httpx.Response(200, json=[])])
def test_unsupported_or_unmatched_native_lookup_falls_back_to_legacy_nfc_id(native_response):
    spool_requests = []

    def handler(request):
        if request.url.path == "/api/v1/info":
            return httpx.Response(200, json={"version": "0.27.0"})
        spool_requests.append(request)
        if "tag" in request.url.params:
            return native_response
        assert dict(request.url.params) == {"extra.nfc_id": "04A2B3C4"}
        return httpx.Response(200, json=[{"id": 42, "extra": {"nfc_id": "04A2B3C4"}}])

    spool = asyncio.run(client_for(handler).get_spool_by_tag_uid("04A2B3C4"))
    assert spool["id"] == 42
    assert len(spool_requests) == 2


def test_failed_capability_probe_still_uses_legacy_lookup():
    def handler(request):
        if request.url.path == "/api/v1/info":
            raise httpx.ConnectError("info unavailable", request=request)
        assert dict(request.url.params) == {"extra.nfc_id": "04A2B3C4"}
        return httpx.Response(200, json=[{"id": 42, "extra": {"nfc_id": "04A2B3C4"}}])

    spool = asyncio.run(client_for(handler).get_spool_by_tag_uid("04A2B3C4"))
    assert spool["id"] == 42


@pytest.mark.parametrize(
    "response",
    [httpx.Response(503), httpx.Response(200, text="not json"), httpx.Response(200, json=[42])],
)
def test_tag_lookup_reports_spoolman_failures_without_exposing_details(response):
    def handler(request):
        if request.url.path == "/api/v1/info":
            return httpx.Response(200, json={"version": "0.26.0"})
        return response

    with pytest.raises(TagLookupError) as exc_info:
        asyncio.run(client_for(handler).get_spool_by_tag_uid("04A2B3C4"))
    assert exc_info.value.status_code == 502
    assert "not json" not in str(exc_info.value)


def test_tag_lookup_reports_denied_credentials():
    def handler(request):
        if request.url.path == "/api/v1/info":
            return httpx.Response(200, json={"version": "0.26.0"})
        return httpx.Response(401, text="secret upstream body")

    with pytest.raises(TagLookupError) as exc_info:
        asyncio.run(client_for(handler).get_spool_by_tag_uid("04A2B3C4"))
    assert "credentials" in str(exc_info.value)
    assert "secret upstream body" not in str(exc_info.value)


def test_assign_tag_uid_preserves_other_extra_fields_and_verifies_write():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["authorization"] == "Bearer secret"
        if request.url.path == "/api/v1/info":
            return httpx.Response(200, json={"version": "0.26.0"})
        if request.url.path == "/api/v1/spool" and request.method == "GET":
            assert dict(request.url.params) == {"extra.nfc_id": "04A2B3C4"}
            return httpx.Response(200, json=[])
        if request.url.path == "/api/v1/spool/42" and request.method == "GET":
            return httpx.Response(200, json={"id": 42, "extra": {"drying_temperature": "55", "note": None}})
        assert request.url.path == "/api/v1/spool/42"
        assert request.method == "PATCH"
        assert json.loads(request.content) == {
            "extra": {"drying_temperature": "55", "note": None, "nfc_id": "04A2B3C4"}
        }
        return httpx.Response(
            200,
            json={"id": 42, "extra": {"drying_temperature": "55", "note": None, "nfc_id": "04A2B3C4"}},
        )

    spool = asyncio.run(client_for(handler).assign_tag_uid(42, "04:a2-b3:c4"))
    assert spool["extra"]["nfc_id"] == "04A2B3C4"
    assert len(requests) == 4


def test_assign_tag_uid_requires_confirmation_before_replacing_existing_uid():
    def handler(request):
        if request.url.path == "/api/v1/info":
            return httpx.Response(200, json={"version": "0.26.0"})
        if request.url.path == "/api/v1/spool":
            return httpx.Response(200, json=[])
        if request.method == "PATCH":
            pytest.fail("An unconfirmed replacement must not be written")
        return httpx.Response(200, json={"id": 42, "extra": {"nfc_id": "AABBCCDD", "note": "keep"}})

    with pytest.raises(TagAssignmentError) as exc_info:
        asyncio.run(client_for(handler).assign_tag_uid(42, "04A2B3C4"))
    assert exc_info.value.status_code == 409
    assert "Confirm replacement" in str(exc_info.value)


def test_assign_tag_uid_replaces_existing_uid_only_when_confirmed():
    def handler(request):
        if request.url.path == "/api/v1/info":
            return httpx.Response(200, json={"version": "0.26.0"})
        if request.url.path == "/api/v1/spool":
            return httpx.Response(200, json=[])
        if request.method == "GET":
            return httpx.Response(200, json={"id": 42, "extra": {"nfc_id": "AABBCCDD", "note": "keep"}})
        assert json.loads(request.content) == {"extra": {"nfc_id": "04A2B3C4", "note": "keep"}}
        return httpx.Response(200, json={"id": 42, "extra": {"nfc_id": "04A2B3C4", "note": "keep"}})

    spool = asyncio.run(client_for(handler).assign_tag_uid(42, "04A2B3C4", replace_existing=True))
    assert spool["extra"] == {"nfc_id": "04A2B3C4", "note": "keep"}


def test_assign_tag_uid_rechecks_for_new_association_before_writing():
    def handler(request):
        if request.url.path == "/api/v1/info":
            return httpx.Response(200, json={"version": "0.26.0"})
        if request.url.path == "/api/v1/spool":
            return httpx.Response(200, json=[{"id": 77, "extra": {"nfc_id": "04A2B3C4"}}])
        pytest.fail("A tag assigned while the page was open must not be reassigned")

    with pytest.raises(TagAssignmentError) as exc_info:
        asyncio.run(client_for(handler).assign_tag_uid(42, "04A2B3C4"))
    assert exc_info.value.status_code == 409
    assert "spool 77" in str(exc_info.value)


def test_assign_tag_uid_rejects_an_unconfirmed_write_response():
    def handler(request):
        if request.url.path == "/api/v1/info":
            return httpx.Response(200, json={"version": "0.26.0"})
        if request.url.path == "/api/v1/spool":
            return httpx.Response(200, json=[])
        if request.method == "GET":
            return httpx.Response(200, json={"id": 42, "extra": {"note": "keep"}})
        return httpx.Response(200, json=[])

    with pytest.raises(TagAssignmentError) as exc_info:
        asyncio.run(client_for(handler).assign_tag_uid(42, "04A2B3C4"))
    assert exc_info.value.status_code == 502
    assert "did not confirm" in str(exc_info.value)

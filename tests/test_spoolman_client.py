import asyncio

import httpx
import pytest

from spoolbud.clients.spoolman import SpoolmanClient


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

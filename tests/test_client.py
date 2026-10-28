import httpx
import pytest

from clavis.client import ClavisClient
from clavis.errors import ClavisAPIError
from clavis.runtime import DEFAULT_UDS


@pytest.mark.parametrize("socket_path", [None, "~/.clavis/custom.sock"])
def test_client_socket_path(monkeypatch, tmp_path, socket_path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    captured = {}

    def transport(*, uds):
        captured["uds"] = uds
        return httpx.MockTransport(lambda request: httpx.Response(200, json={}))

    monkeypatch.setattr("clavis.client.httpx.HTTPTransport", transport)
    client = ClavisClient(**({"uds": socket_path} if socket_path else {}))
    assert captured["uds"] == (str(tmp_path / ".clavis" / "custom.sock") if socket_path else DEFAULT_UDS)
    client._client.close()


def test_client_can_call_api_with_test_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/status"
        return httpx.Response(200, json={"status": "ok", "service": "clavisd"})

    client = ClavisClient(host="http://testserver", transport=httpx.MockTransport(handler))
    assert client.status() == {"status": "ok", "service": "clavisd"}


def test_client_timeout_allows_long_running_board_operations() -> None:
    client = ClavisClient(host="http://testserver", transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})))

    assert client._client.timeout.read == 30.0


def test_client_raises_clavis_api_error_on_4xx_with_detail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/boards/x/connect"
        return httpx.Response(
            409,
            json={"detail": "Failed to connect SAMIDARE board x: Fakernet reliable channel is already connected"},
            request=request,
        )

    client = ClavisClient(host="http://testserver", transport=httpx.MockTransport(handler))

    with pytest.raises(ClavisAPIError) as ei:
        client.connect_board("x")

    err = ei.value
    assert isinstance(err, httpx.HTTPStatusError)
    assert err.response.status_code == 409
    assert err.detail == "Failed to connect SAMIDARE board x: Fakernet reliable channel is already connected"
    assert str(err) == "Failed to connect SAMIDARE board x: Fakernet reliable channel is already connected"


def test_client_raises_clavis_api_error_without_detail_on_bad_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"not-json", request=request)

    client = ClavisClient(host="http://testserver", transport=httpx.MockTransport(handler))

    with pytest.raises(ClavisAPIError) as ei:
        client.request("GET", "/api/status")

    err = ei.value
    assert err.response.status_code == 500
    assert err.detail is None

import httpx

from clavis.client import ClavisClient


def test_client_can_call_api_with_test_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/status"
        return httpx.Response(200, json={"status": "ok", "service": "clavisd"})

    client = ClavisClient(host="http://testserver", transport=httpx.MockTransport(handler))
    assert client.status() == {"status": "ok", "service": "clavisd"}

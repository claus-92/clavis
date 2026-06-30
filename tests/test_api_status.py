from fastapi.testclient import TestClient

from clavis.api.app import create_app


def test_api_status_works() -> None:
    client = TestClient(create_app())
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "clavisd"}

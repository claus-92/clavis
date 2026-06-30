from fastapi.testclient import TestClient

from clavis.api.app import create_app



def test_board_discovery_works() -> None:
    client = TestClient(create_app())
    response = client.post("/api/boards/discover")
    assert response.status_code == 200
    assert [board["board_id"] for board in response.json()] == ["dev-001", "dev-002"]


def test_board_connect_disconnect_and_power() -> None:
    client = TestClient(create_app())
    assert client.post("/api/boards/dev-001/connect").json()["connected"] is True
    assert client.post("/api/boards/dev-001/power/on").json()["powered"] is True
    assert client.post("/api/boards/dev-001/power/off").json()["powered"] is False
    assert client.post("/api/boards/dev-001/disconnect").json()["connected"] is False


def test_parameter_setting_works() -> None:
    client = TestClient(create_app())
    client.post("/api/boards/dev-001/connect")
    global_status = client.post("/api/boards/dev-001/global", json={"mode": "normal"}).json()
    group_status = client.post("/api/boards/dev-001/groups/0", json={"threshold": 20}).json()
    channel_status = client.post("/api/boards/dev-001/channels/0", json={"power": "on", "gain": 2}).json()
    assert global_status["global_options"] == {"mode": "normal"}
    assert group_status["group_options"] == {"0": {"threshold": 20}}
    assert channel_status["channel_options"] == {"0": {"power": "on", "gain": 2}}


def test_invalid_parameter_values_are_rejected() -> None:
    client = TestClient(create_app())
    client.post("/api/boards/dev-001/connect")
    response = client.post("/api/boards/dev-001/channels/0", json={"gain": 3})
    assert response.status_code == 422

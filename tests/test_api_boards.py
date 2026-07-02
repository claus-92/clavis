from fastapi.testclient import TestClient
import pytest

from clavis.api.app import create_app
from tests.fake_plugin import plugin as fake_plugin


def create_test_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("clavis.core.service.load_entry_point_plugins", lambda: [fake_plugin()])
    client = TestClient(create_app())
    response = client.post("/api/boards", json={"board_id": "dev-001", "board_type": "fake", "name": "Fake Board"})
    assert response.status_code == 200
    return client


def test_board_discovery_has_no_default_boards() -> None:
    client = TestClient(create_app())
    response = client.post("/api/boards/discover")
    assert response.status_code == 200
    assert response.json() == []


def test_board_types_do_not_include_builtin_fake_plugin() -> None:
    client = TestClient(create_app())
    response = client.get("/api/board-types")
    assert response.status_code == 200
    assert "fake" not in {board_type["board_type"] for board_type in response.json()}


def test_board_can_be_created_from_generic_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("clavis.core.service.load_entry_point_plugins", lambda: [fake_plugin()])
    client = TestClient(create_app())
    response = client.post("/api/boards", json={"board_id": "dev-003", "board_type": "fake", "name": "Fake Board"})
    assert response.status_code == 200
    assert response.json()["board_id"] == "dev-003"
    assert response.json()["board_type"] == "fake"


def test_board_connect_disconnect_and_power(monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_test_client(monkeypatch)
    assert client.post("/api/boards/dev-001/connect").json()["connected"] is True
    assert client.post("/api/boards/dev-001/power/on").json()["powered"] is True
    assert client.post("/api/boards/dev-001/power/off").json()["powered"] is False
    assert client.post("/api/boards/dev-001/disconnect").json()["connected"] is False


def test_board_acquisition_start_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_test_client(monkeypatch)
    client.post("/api/boards/dev-001/connect")
    client.post("/api/boards/dev-001/power/on")

    started = client.post("/api/boards/dev-001/acquisition/start").json()
    stopped = client.post("/api/boards/dev-001/acquisition/stop").json()

    assert started["acquiring"] is True
    assert stopped["acquiring"] is False


def test_board_acquisition_requires_power(monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_test_client(monkeypatch)
    client.post("/api/boards/dev-001/connect")

    response = client.post("/api/boards/dev-001/acquisition/start")

    assert response.status_code == 409


def test_parameter_setting_works(monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_test_client(monkeypatch)
    client.post("/api/boards/dev-001/connect")
    global_status = client.post("/api/boards/dev-001/global", json={"mode": "normal"}).json()
    group_status = client.post("/api/boards/dev-001/groups/0", json={"threshold": 20}).json()
    channel_status = client.post("/api/boards/dev-001/channels/0", json={"power": "on", "gain": 2}).json()
    assert global_status["global_options"] == {"mode": "normal"}
    assert group_status["group_options"] == {"0": {"threshold": 20}}
    assert channel_status["channel_options"] == {"0": {"power": "on", "gain": 2}}


def test_invalid_parameter_values_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_test_client(monkeypatch)
    client.post("/api/boards/dev-001/connect")
    response = client.post("/api/boards/dev-001/channels/0", json={"gain": 3})
    assert response.status_code == 422

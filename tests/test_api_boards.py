from fastapi.testclient import TestClient
import pytest

from clavis.api.app import create_app
from tests.fake_plugin import FakeBoard
from tests.fake_plugin import plugin as fake_plugin


def create_test_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("clavis.core.service.load_entry_point_plugins", lambda: [fake_plugin()])
    client = TestClient(create_app())
    response = client.post("/api/boards", json={"board_id": "dev-001", "board_type": "fake", "name": "Fake Board"})
    assert response.status_code == 200
    return client


def test_board_discovery_endpoint_is_removed() -> None:
    client = TestClient(create_app())
    response = client.post("/api/boards/discover")
    assert response.status_code == 405


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


def test_deleting_a_connected_board_disconnects_it(monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_test_client(monkeypatch)
    client.post("/api/boards/dev-001/connect")

    response = client.delete("/api/boards/dev-001")

    assert response.status_code == 204
    assert client.get("/api/boards").json() == []


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


def test_invalid_parameter_types_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_test_client(monkeypatch)
    client.post("/api/boards/dev-001/connect")
    response = client.post("/api/boards/dev-001/channels/0", json={"gain": True})
    assert response.status_code == 422
    assert "expected integer" in response.json()["detail"]


def test_get_config_returns_system_config_with_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("clavis.core.service.load_entry_point_plugins", lambda: [fake_plugin()])
    client = TestClient(create_app())

    client.post("/api/boards", json={"board_id": "dev-001", "board_type": "fake", "name": "Fake Board"})
    client.post("/api/boards/dev-001/connect")
    client.post("/api/boards/dev-001/global", json={"mode": "normal"})
    client.post("/api/boards/dev-001/groups/0", json={"threshold": 20})

    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    boards = data["boards"]
    assert len(boards) == 1
    assert boards[0]["config"]["board_id"] == "dev-001"
    assert boards[0]["config"]["board_type"] == "fake"
    assert boards[0]["parameters"]["global"]["mode"] == "normal"
    assert boards[0]["parameters"]["groups"]["0"]["threshold"] == 20


def test_post_config_replaces_all_boards_and_sets_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("clavis.core.service.load_entry_point_plugins", lambda: [fake_plugin()])
    client = TestClient(create_app())

    client.post("/api/boards", json={"board_id": "dev-old", "board_type": "fake", "name": "Old Board"})

    payload = {
        "boards": [
            {
                "config": {"board_id": "dev-new", "board_type": "fake", "name": "New Board"},
                "parameters": {"global": {"mode": "calibration"}, "groups": {}, "channels": {}},
            }
        ]
    }
    response = client.post("/api/config", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["boards"]) == 1
    assert data["boards"][0]["config"]["board_id"] == "dev-new"

    list_resp = client.get("/api/boards")
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["board_id"] == "dev-new"


def test_post_config_uses_parameter_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("clavis.core.service.load_entry_point_plugins", lambda: [fake_plugin()])
    client = TestClient(create_app())
    payload = {
        "boards": [
            {
                "config": {"board_id": "dev-new", "board_type": "fake", "name": "New Board"},
                "parameters": {"global": {"mode": "invalid"}, "groups": {}, "channels": {}},
            }
        ]
    }

    response = client.post("/api/config", json=payload)

    assert response.status_code == 422
    assert "Invalid value for mode" in response.json()["detail"]
    assert client.get("/api/boards").json() == []


def test_invalid_config_does_not_replace_existing_boards(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("clavis.core.service.load_entry_point_plugins", lambda: [fake_plugin()])
    client = TestClient(create_app())
    client.post("/api/boards", json={"board_id": "dev-old", "board_type": "fake", "name": "Old Board"})
    payload = {
        "boards": [
            {
                "config": {"board_id": "dev-new", "board_type": "fake", "name": "New Board"},
                "parameters": {"global": {"mode": "invalid"}, "groups": {}, "channels": {}},
            }
        ]
    }

    response = client.post("/api/config", json=payload)

    assert response.status_code == 422
    assert [board["board_id"] for board in client.get("/api/boards").json()] == ["dev-old"]


def test_config_round_trip_preserves_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("clavis.core.service.load_entry_point_plugins", lambda: [fake_plugin()])
    client = TestClient(create_app())

    client.post("/api/boards", json={"board_id": "dev-001", "board_type": "fake", "name": "Fake Board"})
    client.post("/api/boards/dev-001/connect")
    client.post("/api/boards/dev-001/global", json={"mode": "normal"})
    client.post("/api/boards/dev-001/groups/0", json={"threshold": 20})
    client.post("/api/boards/dev-001/channels/0", json={"gain": 2})

    get_resp = client.get("/api/config")
    assert get_resp.status_code == 200

    post_resp = client.post("/api/config", json=get_resp.json())
    assert post_resp.status_code == 200
    data = post_resp.json()
    assert data["boards"][0]["parameters"]["global"]["mode"] == "normal"
    assert data["boards"][0]["parameters"]["groups"]["0"]["threshold"] == 20
    assert data["boards"][0]["parameters"]["channels"]["0"]["gain"] == 2


def test_connect_errors_return_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_connect(_: FakeBoard) -> None:
        raise RuntimeError("connect failed")

    monkeypatch.setattr(FakeBoard, "connect", fail_connect)
    client = create_test_client(monkeypatch)

    response = client.post("/api/boards/dev-001/connect")

    assert response.status_code == 409
    assert "connect failed" in response.json()["detail"]


def test_disconnect_errors_return_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_test_client(monkeypatch)
    assert client.post("/api/boards/dev-001/connect").status_code == 200

    def fail_disconnect(_: FakeBoard) -> None:
        raise RuntimeError("disconnect failed")

    monkeypatch.setattr(FakeBoard, "disconnect", fail_disconnect)
    response = client.post("/api/boards/dev-001/disconnect")

    assert response.status_code == 409
    assert "disconnect failed" in response.json()["detail"]

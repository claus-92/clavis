import pytest

from clavis.cli import COMMAND_HELP, CommandError, dispatch_command, parse_options


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def status(self) -> dict[str, str]:
        self.calls.append(("status", ()))
        return {"status": "ok"}

    def discover_boards(self) -> list[str]:
        self.calls.append(("discover_boards", ()))
        return ["dev-001"]

    def list_boards(self) -> list[str]:
        self.calls.append(("list_boards", ()))
        return ["dev-001"]

    def get_board(self, board_id: str) -> dict[str, str]:
        self.calls.append(("get_board", (board_id,)))
        return {"board_id": board_id}

    def connect_board(self, board_id: str) -> dict[str, object]:
        self.calls.append(("connect_board", (board_id,)))
        return {"connected": True}

    def disconnect_board(self, board_id: str) -> dict[str, object]:
        self.calls.append(("disconnect_board", (board_id,)))
        return {"connected": False}

    def power_on(self, board_id: str) -> dict[str, object]:
        self.calls.append(("power_on", (board_id,)))
        return {"powered": True}

    def power_off(self, board_id: str) -> dict[str, object]:
        self.calls.append(("power_off", (board_id,)))
        return {"powered": False}

    def get_parameters(self, board_id: str) -> dict[str, str]:
        self.calls.append(("get_parameters", (board_id,)))
        return {"board_id": board_id}

    def set_global(self, board_id: str, options: dict[str, object]) -> dict[str, object]:
        self.calls.append(("set_global", (board_id, options)))
        return options

    def set_group(self, board_id: str, group_id: str, options: dict[str, object]) -> dict[str, object]:
        self.calls.append(("set_group", (board_id, group_id, options)))
        return options

    def set_channel(self, board_id: str, channel_id: str, options: dict[str, object]) -> dict[str, object]:
        self.calls.append(("set_channel", (board_id, channel_id, options)))
        return options

    def get_board_status(self, board_id: str) -> dict[str, str]:
        self.calls.append(("get_board_status", (board_id,)))
        return {"board_id": board_id}


def test_dispatch_status_uses_client() -> None:
    client = FakeClient()

    assert dispatch_command(["status"], client) == {"status": "ok"}
    assert client.calls == [("status", ())]


def test_dispatch_set_channel_parses_options() -> None:
    client = FakeClient()

    result = dispatch_command(["boards", "set-channel", "dev-001", "0", "gain=2", "power=on"], client)

    assert result == {"gain": 2, "power": "on"}
    assert client.calls == [("set_channel", ("dev-001", "0", {"gain": 2, "power": "on"}))]


def test_dispatch_help_returns_help_text() -> None:
    assert dispatch_command(["help"], FakeClient()) == COMMAND_HELP.rstrip()


def test_parse_options_accepts_ints_booleans_and_strings() -> None:
    assert parse_options(["gain=2", "enabled=true", "mode=normal"]) == {
        "gain": 2,
        "enabled": True,
        "mode": "normal",
    }


def test_dispatch_rejects_unknown_command() -> None:
    with pytest.raises(CommandError, match="Unknown command"):
        dispatch_command(["missing"], FakeClient())


def test_parse_options_rejects_invalid_options() -> None:
    with pytest.raises(CommandError, match="Options must be KEY=VALUE"):
        parse_options(["gain"])

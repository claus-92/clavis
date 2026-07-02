import sys
from types import SimpleNamespace

import pytest

from clavis.cli import COMMAND_HELP, CommandError, build_create_config, dispatch_command, format_result, parse_options, setup_shell_history


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

    def list_board_types(self) -> list[dict[str, object]]:
        self.calls.append(("list_board_types", ()))
        return [
            {
                "board_type": "fake",
                "display_name": "Fake Board",
                "config_schema": {
                    "properties": {
                        "board_id": {"title": "Board Id", "type": "string"},
                        "name": {"title": "Name", "type": "string"},
                    },
                    "required": ["board_id", "name"],
                },
            },
            {
                "board_type": "samidare",
                "display_name": "SAMIDARE",
                "config_schema": {
                    "properties": {
                        "board_id": {"title": "Board Id", "type": "string"},
                        "name": {"title": "Name", "type": "string"},
                        "host": {"title": "Host", "type": "string"},
                    },
                    "required": ["board_id", "name", "host"],
                },
            },
        ]

    def create_board(self, config: dict[str, object]) -> dict[str, object]:
        self.calls.append(("create_board", (config,)))
        return config

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


def test_dispatch_create_prompts_for_missing_required_fields() -> None:
    client = FakeClient()
    answers = iter(["samidare", "dev-003", "SAMIDARE_003", "192.168.1.10"])

    result = dispatch_command(["boards", "create"], client, prompt=lambda _: next(answers))

    assert result == {
        "board_type": "samidare",
        "board_id": "dev-003",
        "name": "SAMIDARE_003",
        "host": "192.168.1.10",
    }
    assert client.calls == [
        ("list_board_types", ()),
        (
            "create_board",
            (
                {
                    "board_type": "samidare",
                    "board_id": "dev-003",
                    "name": "SAMIDARE_003",
                    "host": "192.168.1.10",
                },
            ),
        ),
    ]


def test_build_create_config_keeps_explicit_required_fields() -> None:
    client = FakeClient()

    result = build_create_config(
        ["board_type=samidare", "board_id=dev-003", "name=SAMIDARE_003", "host=192.168.1.10"],
        client,
        prompt=lambda _: pytest.fail("should not prompt"),
    )

    assert result == {
        "board_type": "samidare",
        "board_id": "dev-003",
        "name": "SAMIDARE_003",
        "host": "192.168.1.10",
    }


def test_build_create_config_rejects_unknown_board_type() -> None:
    with pytest.raises(CommandError, match="Unknown board type"):
        build_create_config(["board_type=missing"], FakeClient())


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


def test_setup_shell_history_loads_and_registers_writer(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    calls: list[tuple[str, object]] = []
    history_path = tmp_path / "history"

    fake_readline = SimpleNamespace(
        read_history_file=lambda path: calls.append(("read", path)),
        set_history_length=lambda length: calls.append(("length", length)),
        write_history_file=lambda path: calls.append(("write", path)),
    )

    def register(callback) -> None:
        calls.append(("register", callback))
        callback()

    monkeypatch.setitem(sys.modules, "readline", fake_readline)
    monkeypatch.setitem(sys.modules, "atexit", SimpleNamespace(register=register))

    setup_shell_history(history_path)

    assert calls == [
        ("read", str(history_path)),
        ("length", 1000),
        ("register", calls[2][1]),
        ("write", str(history_path)),
    ]


def test_parse_options_rejects_invalid_options() -> None:
    with pytest.raises(CommandError, match="Options must be KEY=VALUE"):
        parse_options(["gain"])


def test_format_result_formats_board_list_as_table() -> None:
    result = format_result(
        [
            {
                "board_id": "dev-001",
                "name": "Fake Board_TPC_1",
                "asic": "SAMPA_v4",
                "fpga": "Artix_Ultrascale_Plus",
                "firmware_version": "FW_v_1_2_3",
                "board_type": "fake",
            }
        ]
    )

    assert "board_id" in result
    assert "dev-001" in result
    assert "Fake Board_TPC_1" in result
    assert "{'" not in result


def test_format_result_formats_status_as_key_values() -> None:
    result = format_result({"status": "ok", "service": "clavisd"})

    assert result == "Status   ok\nService  clavisd"


def test_format_result_formats_parameters_as_sections() -> None:
    result = format_result(
        {
            "generalParameters": [
                {
                    "name": "mode",
                    "type": "string",
                    "defaultValue": "normal",
                    "options": ["normal", "calibration"],
                    "description": "Operating mode",
                }
            ],
            "channelParameters": [],
            "groupParameters": [],
        }
    )

    assert "General Parameters" in result
    assert "Channel Parameters" in result
    assert "mode" in result
    assert "normal, calibration" in result
    assert "No parameters." in result


def test_format_result_formats_board_types_without_inline_schema_repr() -> None:
    result = format_result(
        [
            {
                "board_type": "fake",
                "display_name": "Fake Board",
                "config_schema": {"required": ["board_id", "name"]},
            }
        ]
    )

    assert "board_type" in result
    assert "Fake Board" in result
    assert "Config schema for fake" in result
    assert '"required"' in result

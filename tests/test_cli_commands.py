import asyncio
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from clavis.cli import (
    app,
    format_result,
    parse_options,
)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def status(self) -> dict[str, str]:
        self.calls.append(("status", ()))
        return {"status": "ok"}

    def list_boards(self) -> list[dict[str, Any]]:
        self.calls.append(("list_boards", ()))
        return [{"board_id": "dev-001", "name": "TestBoard"}]

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

    def get_board_config(self, board_id: str) -> dict[str, Any]:
        self.calls.append(("get_board_config", (board_id,)))
        return {"board_id": board_id, "board_type": "fake"}

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

    def start_acquisition(self, board_id: str) -> dict[str, object]:
        self.calls.append(("start_acquisition", (board_id,)))
        return {"acquiring": True}

    def stop_acquisition(self, board_id: str) -> dict[str, object]:
        self.calls.append(("stop_acquisition", (board_id,)))
        return {"acquiring": False}

    def get_parameters(self, board_id: str) -> dict[str, list[dict[str, Any]]]:
        self.calls.append(("get_parameters", (board_id,)))
        return {
            "generalParameters": [
                {
                    "name": "mode",
                    "type": "string",
                    "defaultValue": "normal",
                    "options": ["normal", "calibration"],
                    "description": "Test mode",
                }
            ],
            "groupParameters": [
                {
                    "name": "threshold",
                    "type": "integer",
                    "defaultValue": 10,
                    "options": [5, 10, 20],
                    "description": "Test threshold",
                }
            ],
            "channelParameters": [
                {
                    "name": "gain",
                    "type": "integer",
                    "defaultValue": 1,
                    "options": [1, 2, 4, 8],
                    "description": "Test gain",
                }
            ],
        }

    def set_global(self, board_id: str, options: dict[str, object]) -> dict[str, object]:
        self.calls.append(("set_global", (board_id, options)))
        return options

    def set_group(self, board_id: str, group_id: str, options: dict[str, object]) -> dict[str, object]:
        self.calls.append(("set_group", (board_id, group_id, options)))
        return options

    def set_channel(self, board_id: str, channel_id: str, options: dict[str, object]) -> dict[str, object]:
        self.calls.append(("set_channel", (board_id, channel_id, options)))
        return options

    def get_board_status(self, board_id: str) -> dict[str, Any]:
        self.calls.append(("get_board_status", (board_id,)))
        return {
            "board_id": board_id,
            "connected": True,
            "powered": False,
            "acquiring": False,
            "global_options": {
                "calibration_ready": False,
                "calibration_failed": True,
                "calibration_state": "done",
                "calibration_status_raw": "0x0000000e",
                "calibration_clock_done_mask": "0xf",
                "calibration_lane_done_mask": "0xffffffffff",
                "calibration_incomplete_lane_index": 1,
                "calibration_debug_error": None,
            },
            "group_options": {},
            "channel_options": {},
        }

    def get_config(self) -> dict[str, Any]:
        self.calls.append(("get_config", ()))
        return {
            "boards": [
                {
                    "config": {"board_id": "dev-001", "board_type": "fake", "name": "Fake Board"},
                    "parameters": {"global": {"mode": "normal"}, "groups": {}, "channels": {}},
                }
            ]
        }

    def apply_config(self, system_config: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("apply_config", (system_config,)))
        return system_config


runner = CliRunner()


def test_cli_status(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr("clavis.cli.client", lambda: fake)

    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "ok" in result.output
    assert fake.calls == [("status", ())]


def test_cli_host_can_come_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    fake = FakeClient()

    def fake_client(*, host: str | None, uds: str) -> FakeClient:
        captured.update(host=host, uds=uds)
        return fake

    monkeypatch.setattr("clavis.cli.ClavisClient", fake_client)

    result = runner.invoke(
        app,
        ["status"],
        env={"CLAVIS_HOST": "http://127.0.0.1:8000"},
    )

    assert result.exit_code == 0
    assert captured["host"] == "http://127.0.0.1:8000"


def test_cli_socket_can_come_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    fake = FakeClient()

    def fake_client(*, host: str | None, uds: str) -> FakeClient:
        captured.update(host=host, uds=uds)
        return fake

    monkeypatch.setattr("clavis.cli.ClavisClient", fake_client)

    result = runner.invoke(
        app,
        ["status"],
        env={"CLAVIS_UDS": "/tmp/test-clavisd.sock"},
    )

    assert result.exit_code == 0
    assert captured == {"host": None, "uds": "/tmp/test-clavisd.sock"}


def test_cli_boards_list(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr("clavis.cli.client", lambda: fake)

    result = runner.invoke(app, ["boards", "list"])
    assert result.exit_code == 0
    assert "dev-001" in result.output


def test_cli_boards_set_global_parses_options(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr("clavis.cli.client", lambda: fake)

    result = runner.invoke(app, ["boards", "set-global", "dev-001", "gain=2", "power=true"])
    assert result.exit_code == 0
    assert fake.calls == [("set_global", ("dev-001", {"gain": 2, "power": True}))]


def test_cli_boards_create_prompts(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr("clavis.cli.client", lambda: fake)

    # Simulate interactive prompts via stdin (board_type + required fields)
    user_input = "samidare\ndev-003\nSAMIDARE_003\n192.168.1.10\n"
    result = runner.invoke(app, ["boards", "create"], input=user_input)
    assert result.exit_code == 0
    assert any("create_board" == c[0] for c in fake.calls)


def test_parse_options() -> None:
    assert parse_options(["gain=2", "enabled=true", "mode=normal"]) == {
        "gain": 2,
        "enabled": True,
        "mode": "normal",
    }


def test_parse_options_rejects_bad() -> None:
    with pytest.raises(Exception):  # typer.BadParameter is raised inside commands
        parse_options(["bad"])


def test_format_result_still_works() -> None:
    out = format_result({"status": "ok"})
    assert "Status" in out
    assert "ok" in out


def test_cli_help_shows_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "boards" in result.output
    assert "tui" in result.output
    assert "status" in result.output


def test_cli_boards_help() -> None:
    result = runner.invoke(app, ["boards", "--help"])
    assert result.exit_code == 0
    assert "set-global" in result.output
    assert "create" in result.output
    assert "discover" not in result.output


def test_cli_command_help_flag() -> None:
    result = runner.invoke(app, ["boards", "set-global", "--help"])
    assert result.exit_code == 0
    assert "KEY=VALUE" in result.output or "options" in result.output.lower()


def test_tui_imports_and_instantiates() -> None:
    from clavis.tui.app import ClavisTUI

    tui = ClavisTUI()
    assert tui is not None
    # run_tui is not called here; it would start the app


def test_tui_plain_key_refresh_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr("clavis.tui.app.ClavisClient", lambda **_: fake)

    async def run() -> None:
        from clavis.tui.app import ClavisTUI

        async with ClavisTUI().run_test() as pilot:
            before = len([call for call in fake.calls if call[0] == "list_boards"])
            await pilot.press("r")
            after = len([call for call in fake.calls if call[0] == "list_boards"])

        assert after == before + 1

    asyncio.run(run())


def test_tui_new_board_enter_advances_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr("clavis.tui.app.ClavisClient", lambda **_: fake)

    async def run() -> None:
        from textual.widgets import Static

        from clavis.tui.app import ClavisTUI

        async with ClavisTUI().run_test() as pilot:
            await pilot.press("n")
            await pilot.press("f", "a", "k", "e", "enter")
            status = pilot.app.screen.query_one("#create-status", Static)

        assert "Board Id" in str(status.render())

    asyncio.run(run())


def test_tui_enter_on_board_opens_detail_screen(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr("clavis.tui.app.ClavisClient", lambda **_: fake)

    async def run() -> None:
        from textual.widgets import DataTable, Static

        from clavis.tui.app import ClavisTUI
        from clavis.tui.screens import BoardDetailScreen

        async with ClavisTUI().run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()

            assert isinstance(pilot.app.screen, BoardDetailScreen)
            info = pilot.app.screen.query_one("#detail-status", Static)
            rendered_info = str(info.render())
            assert "TestBoard" in rendered_info
            assert "Connected  yes" in rendered_info
            assert "Cal State  done" in rendered_info
            assert "Lane       1" in rendered_info
            table = pilot.app.screen.query_one("#parameters-table", DataTable)
            assert table.row_count == 3

    asyncio.run(run())


def test_tui_detail_c_connects_without_creating(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr("clavis.tui.app.ClavisClient", lambda **_: fake)

    async def run() -> None:
        from clavis.tui.app import ClavisTUI

        async with ClavisTUI().run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("c")
            await pilot.pause()

        assert ("connect_board", ("dev-001",)) in fake.calls
        assert not any(call[0] == "create_board" for call in fake.calls)

    asyncio.run(run())


def test_cli_config_dump(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake = FakeClient()
    monkeypatch.setattr("clavis.cli.client", lambda: fake)

    result = runner.invoke(app, ["config", "dump"])
    assert result.exit_code == 0
    assert "dev-001" in result.output
    assert ("get_config", ()) in fake.calls


def test_cli_config_dump_to_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake = FakeClient()
    monkeypatch.setattr("clavis.cli.client", lambda: fake)

    out_path = tmp_path / "config.json"
    result = runner.invoke(app, ["config", "dump", "--output", str(out_path)])
    assert result.exit_code == 0
    assert out_path.exists()
    assert "dev-001" in out_path.read_text()
    assert ("get_config", ()) in fake.calls


def test_cli_config_load(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake = FakeClient()
    monkeypatch.setattr("clavis.cli.client", lambda: fake)

    cfg_path = tmp_path / "config.json"
    cfg_path.write_text('{"boards": [{"config": {"board_id": "dev-001", "board_type": "fake", "name": "Fake Board"}, "parameters": {"global": {}, "groups": {}, "channels": {}}}]}')

    result = runner.invoke(app, ["config", "load", str(cfg_path)])
    assert result.exit_code == 0
    assert any(c[0] == "apply_config" for c in fake.calls)


def test_cli_config_load_rejects_bad_file(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr("clavis.cli.client", lambda: fake)

    result = runner.invoke(app, ["config", "load", "/nonexistent/file.json"])
    assert result.exit_code != 0


def test_tui_detail_edits_global_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr("clavis.tui.app.ClavisClient", lambda **_: fake)

    async def run() -> None:
        from clavis.tui.app import ClavisTUI

        async with ClavisTUI().run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("down", "enter")
            await pilot.pause()

        assert ("set_global", ("dev-001", {"mode": "calibration"})) in fake.calls

    asyncio.run(run())

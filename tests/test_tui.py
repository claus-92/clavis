import asyncio
from threading import Event, Lock
from unittest.mock import Mock

import pytest
from textual.widgets import DataTable, Input

from clavis.client import ClavisClient
from clavis.tui.app import ClavisTUI
from clavis.tui.screens import BoardDetailScreen, TextInputModal


@pytest.fixture
def dashboard(monkeypatch):
    client = Mock(spec=ClavisClient)
    boards = [{"board_id": f"b{i}", "name": f"Board {i}"} for i in range(1, 4)]
    client.list_boards.side_effect = lambda: list(boards)
    client.get_board_status.return_value = {"connected": True}
    client.get_board.return_value = boards[0]
    client.get_parameters.return_value = {
        "generalParameters": [], "groupParameters": [], "channelParameters": []
    }
    monkeypatch.setattr("clavis.tui.app.ClavisClient", lambda **kwargs: client)
    return ClavisTUI(), client, boards


def test_selection_keys_and_refresh(dashboard):
    app, client, boards = dashboard

    async def scenario():
        async with app.run_test() as pilot:
            table = app.query_one("#boards-table", DataTable)
            await pilot.press("space", "down", "space")
            assert app._marked_board_ids == {"b1", "b2"}
            assert str(table.get_row_at(0)[0]) == "[x]"
            boards.reverse()
            app.refresh_boards()
            assert app._selected_board_id() == "b2"
            assert app._marked_board_ids == {"b1", "b2"}
            assert str(table.get_row_at(2)[0]) == "[x]"

            # A transient API failure must not silently discard the selection.
            client.list_boards.side_effect = OSError("offline")
            app.refresh_boards()
            assert app._marked_board_ids == {"b1", "b2"}
            client.list_boards.side_effect = lambda: list(boards)
            boards.pop()  # Remove b1 from the daemon's list.
            app.refresh_boards()
            assert app._marked_board_ids == {"b2"}

            await pilot.press("ctrl+a")
            assert app._marked_board_ids == {"b2", "b3"}
            await pilot.press("ctrl+a")
            assert app._marked_board_ids == set()
            assert str(table.get_row_at(0)[0]) == "[ ]"

    asyncio.run(scenario())


@pytest.mark.parametrize("key,method", [
    ("c", "connect_board"),
    ("x", "disconnect_board"),
    ("o", "power_on"),
    ("f", "power_off"),
    ("a", "arm_acquisition"),
    ("s", "start_acquisition"),
    ("t", "stop_acquisition"),
])
def test_commands_target_marked_boards_or_current_row(dashboard, key, method):
    app, client, _ = dashboard

    async def scenario():
        async with app.run_test() as pilot:
            await pilot.press("space", "down", "space", "down", key)
            await app.workers.wait_for_complete()
            operation = getattr(client, method)
            assert {call.args[0] for call in operation.call_args_list} == {"b1", "b2"}
            assert operation.call_count == 2
            assert app._marked_board_ids == {"b1", "b2"}
            operation.reset_mock()

            # Clear marks and retain the cursor on the unmarked third row.
            await pilot.press("ctrl+a", "ctrl+a", key)
            await app.workers.wait_for_complete()
            operation.assert_called_once_with("b3")

    asyncio.run(scenario())


def test_commands_overlap_and_partial_failure_does_not_stop_other_boards(dashboard):
    app, client, _ = dashboard
    both_started = Event()
    release = Event()
    lock = Lock()
    started = set()

    def power_on(board_id):
        with lock:
            started.add(board_id)
            if len(started) == 2:
                both_started.set()
        if not release.wait(5):
            raise TimeoutError("test did not release operation")
        if board_id == "b2":
            raise ValueError("power failed")

    client.power_on.side_effect = power_on

    async def scenario():
        async with app.run_test() as pilot:
            try:
                await pilot.press("space", "down", "space", "o")
                assert await asyncio.to_thread(both_started.wait, 3), "Commands were serialized"
                assert app._action_running
                status_calls = client.get_board_status.call_count
                # The UI remains responsive; changing marks cannot change in-flight targets.
                await pilot.press("down", "space", "c", "d", "L", "r")
                assert app._marked_board_ids == {"b1", "b2", "b3"}
                assert len(app.screen_stack) == 1
                client.connect_board.assert_not_called()
                assert client.get_board_status.call_count == status_calls
                assert started == {"b1", "b2"}
            finally:
                release.set()
                await app.workers.wait_for_complete()
            assert not app._action_running
            assert "1/2 succeeded" in app._operation_message
            assert "b2: power failed" in app._operation_message
            assert client.get_board_status.call_count > status_calls

    asyncio.run(scenario())


def test_detail_and_input_keep_their_own_keyboard_scope(dashboard):
    app, client, _ = dashboard

    async def scenario():
        async with app.run_test() as pilot:
            await pilot.press("ctrl+a", "enter")
            assert isinstance(app.screen, BoardDetailScreen)
            await pilot.press("space", "ctrl+a", "o")
            assert app._marked_board_ids == {"b1", "b2", "b3"}
            client.power_on.assert_called_once_with("b1")
            await pilot.press("escape")
            await pilot.pause()
            assert len(app.screen_stack) == 1

            await app.push_screen(TextInputModal("Path"))
            await pilot.press("a", "b", "ctrl+a", "z", "space")
            # In Textual inputs Ctrl+A moves to the beginning of the line.
            assert app.screen.query_one(Input).value == "z ab"
            assert app._marked_board_ids == {"b1", "b2", "b3"}

    asyncio.run(scenario())


def test_empty_dashboard(dashboard):
    app, client, boards = dashboard
    boards.clear()

    async def scenario():
        async with app.run_test() as pilot:
            await pilot.press("space", "ctrl+a", "o")
            assert app._marked_board_ids == set()
            assert not app._action_running
            client.power_on.assert_not_called()

    asyncio.run(scenario())

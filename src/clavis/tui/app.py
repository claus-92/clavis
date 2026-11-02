"""Keyboard-driven Clavis terminal interface."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Callable, Optional

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.coordinate import Coordinate
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import DataTable, Header, Static

from clavis.branding import get_version
from clavis.client import ClavisClient
from clavis.runtime import DEFAULT_UDS
from clavis.tui.screens import (
    BoardDetailScreen,
    CreateBoardScreen,
    MessageModal,
    TextInputModal,
    legend_text,
)


class ClavisTUI(App[None]):
    """Live board status dashboard + full command actions via keyboard."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("n", "create_board", "New board"),
        ("D", "dump_config", "Dump config"),
        ("L", "load_config", "Load config"),
        ("d", "open_detail", "Detail"),
        ("space", "toggle_board", "Select board"),
        ("ctrl+a", "select_all", "Select/deselect all"),
        ("c", "connect", "Connect"),
        ("x", "disconnect", "Disconnect"),
        ("o", "power_on", "Power on"),
        ("f", "power_off", "Power off"),
        ("a", "arm_acquisition", "Arm acquisition"),
        ("s", "start_acquisition", "Start (local source)"),
        ("t", "stop_acquisition", "Disarm acquisition"),
    ]

    CSS = """
    Screen { background: #0f1117; }
    DataTable { height: 1fr; }
    .status-bar { dock: bottom; background: #1a1c24; padding: 0 1; }
    .detail-legend {
        color: #e2e8f0;
        background: #1a1c24;
        padding: 0 1;
    }
    .help-text { color: #888; }
    .detail-title {
        text-style: bold;
        color: #f0f4ff;
        background: #151924;
        padding: 1 2;
    }
    .detail-status {
        background: #0f1320;
        border: tall #2d3748;
        padding: 1 2;
    }
    .detail-help {
        color: #9fb3c8;
        padding: 0 1;
    }
    .detail-message {
        color: #8a94a6;
        dock: bottom;
        background: #151924;
        padding: 0 1;
    }
    """

    TITLE = f"CLAVIS {get_version()}"
    SUB_TITLE = "Control Layer for Acquisition-board Validation and Interface Services"

    boards: reactive[list[dict[str, Any]]] = reactive([])
    client: ClavisClient
    _last_message: str = ""

    def __init__(self, host: Optional[str] = None, uds: str = DEFAULT_UDS) -> None:
        super().__init__()
        self.client = ClavisClient(host=host, uds=uds)
        self._marked_board_ids: set[str] = set()
        self._action_running = False
        self._operation_message = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            DataTable(id="boards-table", zebra_stripes=True, cursor_type="row"),
            id="main",
        )
        yield Static(id="selection-status", markup=False)
        yield Static(legend_text(self.BINDINGS), classes="status-bar")

    def on_mount(self) -> None:
        table: DataTable = self.query_one("#boards-table", DataTable)
        table.add_columns("selected", "board_id", "name", "connected", "powered", "acquiring")
        table.focus()
        self.refresh_boards()
        self.set_interval(2.0, self.refresh_boards)

    def refresh_boards(self) -> None:
        # Do not poll hardware during a command or behind another screen.
        if self._action_running or not self._dashboard_active():
            return
        table: DataTable = self.query_one("#boards-table", DataTable)
        selected_id = self._selected_board_id()
        try:
            boards = self.client.list_boards() or []
            enriched: list[dict[str, Any]] = []
            for b in boards:
                bid = b.get("board_id") if isinstance(b, dict) else None
                if not bid:
                    continue
                try:
                    st = self.client.get_board_status(bid) or {}
                except Exception:
                    st = {}
                enriched.append(
                    {
                        "board_id": bid,
                        "name": (b.get("name") if isinstance(b, dict) else "") or "",
                        "connected": st.get("connected", False),
                        "powered": st.get("powered", False),
                        "acquiring": st.get("acquiring", False),
                    }
                )
            self.boards = enriched
        except Exception as exc:
            self._operation_message = f"Refresh failed: {exc}"
            self._update_selection_status()
            return

        self._marked_board_ids.intersection_update(b["board_id"] for b in self.boards)

        table.clear()
        target_row = 0
        for index, b in enumerate(self.boards):
            table.add_row(
                Text("[x]" if b["board_id"] in self._marked_board_ids else "[ ]"),
                b["board_id"],
                b["name"],
                "yes" if b["connected"] else "no",
                "yes" if b["powered"] else "no",
                "yes" if b["acquiring"] else "no",
                key=b["board_id"],
            )
            if selected_id and b["board_id"] == selected_id:
                target_row = index
        if table.row_count:
            table.move_cursor(row=target_row)
        self._update_selection_status()

    def _dashboard_active(self) -> bool:
        return self.screen is self.screen_stack[0]

    def _update_selection_status(self) -> None:
        message = f"{len(self._marked_board_ids)}/{len(self.boards)} selected"
        if not self._marked_board_ids:
            message += " | Commands target the current row"
        if self._operation_message:
            message += f" | {self._operation_message}"
        self.query_one("#selection-status", Static).update(message)

    def _render_selection(self) -> None:
        table = self.query_one("#boards-table", DataTable)
        for index, board in enumerate(self.boards):
            board_id = board["board_id"]
            table.update_cell_at(
                Coordinate(index, 0), Text("[x]" if board_id in self._marked_board_ids else "[ ]")
            )
        self._update_selection_status()

    def action_toggle_board(self) -> None:
        board_id = self._selected_board_id()
        if not board_id:
            return
        if board_id in self._marked_board_ids:
            self._marked_board_ids.remove(board_id)
        else:
            self._marked_board_ids.add(board_id)
        self._render_selection()

    def action_select_all(self) -> None:
        if not self._dashboard_active():
            return
        board_ids = {board["board_id"] for board in self.boards}
        self._marked_board_ids = set() if self._marked_board_ids == board_ids else board_ids
        self._render_selection()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "boards-table" or isinstance(self.screen, ModalScreen):
            return
        self.action_open_detail()

    def action_refresh(self) -> None:
        if isinstance(self.screen, ModalScreen):
            return
        self.refresh_boards()

    def action_open_detail(self) -> None:
        if not self._dashboard_available():
            return
        board_id = self._selected_board_id()
        if board_id:
            self._open_board_detail(board_id)

    def action_connect(self) -> None:
        self._perform_board_action("connected", self.client.connect_board)

    def action_disconnect(self) -> None:
        self._perform_board_action("disconnected", self.client.disconnect_board)

    def action_power_on(self) -> None:
        self._perform_board_action("powered on", self.client.power_on)

    def action_power_off(self) -> None:
        self._perform_board_action("powered off", self.client.power_off)

    def action_start_acquisition(self) -> None:
        self._perform_board_action("acquisition start requested", self.client.start_acquisition)

    def action_arm_acquisition(self) -> None:
        self._perform_board_action("acquisition armed", self.client.arm_acquisition)

    def action_stop_acquisition(self) -> None:
        self._perform_board_action("acquisition stopped", self.client.stop_acquisition)

    def _selected_board_id(self) -> Optional[str]:
        if not self._dashboard_active():
            return None
        table = self.query_one("#boards-table", DataTable)
        if table.row_count == 0 or table.cursor_row < 0:
            return None
        try:
            row = table.get_row_at(table.cursor_row)
        except Exception:
            return None
        return str(row[1]) if row else None

    def _dashboard_available(self) -> bool:
        if not self._dashboard_active():
            return False
        if self._action_running:
            self.notify("A board operation is still running", severity="warning")
            return False
        return True

    def _perform_board_action(self, label: str, fn: Callable[[str], Any]) -> None:
        if not self._dashboard_available():
            return
        targets = [b["board_id"] for b in self.boards if b["board_id"] in self._marked_board_ids]
        if not targets:
            board_id = self._selected_board_id()
            targets = [board_id] if board_id else []
        if not targets:
            self.notify("No board selected", severity="warning")
            return
        self._action_running = True
        self._operation_message = f"{label}: running (0/{len(targets)})"
        self._update_selection_status()

        async def perform() -> None:
            failures: dict[str, str] = {}
            completed = 0

            async def apply(board_id: str) -> None:
                nonlocal completed
                try:
                    await asyncio.to_thread(fn, board_id)
                except Exception as exc:
                    failures[board_id] = str(exc)
                completed += 1
                self._operation_message = f"{label}: running ({completed}/{len(targets)})"
                self._update_selection_status()

            try:
                await asyncio.gather(*(apply(board_id) for board_id in targets))
                summary = f"{label}: {len(targets) - len(failures)}/{len(targets)} succeeded"
                if failures:
                    summary += "; failed: " + "; ".join(f"{bid}: {error}" for bid, error in failures.items())
                self._operation_message = summary
                self.notify(summary, severity="error" if failures else "information", timeout=10)
            finally:
                self._action_running = False
                self._update_selection_status()
                self.refresh_boards()

        self.run_worker(perform(), group="board-actions")

    def action_create_board(self) -> None:
        if not self._dashboard_available():
            return
        self._create_board()

    def action_dump_config(self) -> None:
        if not self._dashboard_available():
            return
        self._dump_config()

    def action_load_config(self) -> None:
        if not self._dashboard_available():
            return
        self._load_config()

    def _dump_config(self) -> None:
        async def do_dump() -> None:
            filepath = await self.push_screen_wait(TextInputModal("File path to save config"))
            if not filepath:
                return
            try:
                config = self.client.get_config()
                Path(filepath).write_text(json.dumps(config, indent=2))
                self._show_message(f"Config saved to {filepath}")
            except Exception as exc:
                self._show_message(f"Config dump failed: {exc}")

        self.run_worker(do_dump())

    def _load_config(self) -> None:
        async def do_load() -> None:
            filepath = await self.push_screen_wait(TextInputModal("File path to load config from"))
            if not filepath:
                return
            try:
                data = json.loads(Path(filepath).read_text())
                self.client.apply_config(data)
                self._show_message(f"Config loaded from {filepath}")
                self.refresh_boards()
            except Exception as exc:
                self._show_message(f"Config load failed: {exc}")

        self.run_worker(do_load())

    def _show_message(self, msg: str) -> None:
        self._last_message = msg
        self.push_screen(MessageModal(msg))

    def _create_board(self) -> None:
        async def do_create() -> None:
            cfg = await self.push_screen_wait(CreateBoardScreen(self.client))
            if cfg:
                try:
                    result = self.client.create_board(cfg)
                    self._show_message(f"Created: {result}")
                    self.refresh_boards()
                except Exception as exc:
                    self._show_message(f"Create failed: {exc}")

        self.run_worker(do_create())

    def _open_board_detail(self, board_id: str) -> None:
        board = next(
            (board for board in self.boards if str(board.get("board_id")) == board_id),
            {"board_id": board_id},
        )
        self.push_screen(BoardDetailScreen(self.client, board), lambda _: self.refresh_boards())


def run_tui(host: Optional[str] = None, uds: str = DEFAULT_UDS) -> None:
    ClavisTUI(host=host, uds=uds).run()

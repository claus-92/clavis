"""Keyboard-driven Clavis terminal interface."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Static

from clavis.client import ClavisClient
from clavis.runtime import DEFAULT_UDS
from clavis.tui.screens import (
    BoardDetailScreen,
    CreateBoardScreen,
    MessageModal,
    TextInputModal,
)


class ClavisTUI(App[None]):
    """Live board status dashboard + full command actions via keyboard."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("n", "create_board", "New board"),
        ("D", "dump_config", "Dump config"),
        ("L", "load_config", "Load config"),
    ]

    CSS = """
    Screen { background: #0f1117; }
    DataTable { height: 1fr; }
    .status-bar { dock: bottom; background: #1a1c24; padding: 0 1; }
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
    .detail-actions {
        color: #e2e8f0;
        background: #1a1c24;
        padding: 0 1;
        text-style: bold;
    }
    .detail-message {
        color: #8a94a6;
        dock: bottom;
        background: #151924;
        padding: 0 1;
    }
    """

    TITLE = "clavis tui"
    SUB_TITLE = "Board Status (↑↓ select, Enter=actions, n=new board, D=dump config, L=load config, r=refresh, q=quit)"

    boards: reactive[list[dict[str, Any]]] = reactive([])
    client: ClavisClient
    _last_message: str = ""

    def __init__(self, host: Optional[str] = None, uds: str = DEFAULT_UDS) -> None:
        super().__init__()
        self.client = ClavisClient(host=host, uds=uds)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            DataTable(id="boards-table", zebra_stripes=True, cursor_type="row"),
            id="main",
        )
        yield Static(
            "n: new board   Enter: actions   D: dump config   L: load config   r: refresh   q: quit",
            classes="status-bar",
        )
        yield Footer()

    def on_mount(self) -> None:
        table: DataTable = self.query_one("#boards-table", DataTable)
        table.add_columns("board_id", "name", "connected", "powered", "acquiring")
        table.focus()
        self.refresh_boards()
        self.set_interval(2.0, self.refresh_boards)

    def refresh_boards(self) -> None:
        table: DataTable = self.query_one("#boards-table", DataTable)
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
        except Exception:
            self.boards = []

        table.clear()
        for b in self.boards:
            table.add_row(
                b["board_id"],
                b["name"],
                "yes" if b["connected"] else "no",
                "yes" if b["powered"] else "no",
                "yes" if b["acquiring"] else "no",
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "boards-table" or isinstance(self.screen, ModalScreen):
            return
        try:
            row = event.data_table.get_row(event.row_key)
        except Exception:
            return
        if row:
            self._open_board_detail(str(row[0]))

    def action_refresh(self) -> None:
        if isinstance(self.screen, ModalScreen):
            return
        self.refresh_boards()

    def action_create_board(self) -> None:
        if isinstance(self.screen, ModalScreen):
            return
        self._create_board()

    def action_dump_config(self) -> None:
        if isinstance(self.screen, ModalScreen):
            return
        self._dump_config()

    def action_load_config(self) -> None:
        if isinstance(self.screen, ModalScreen):
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

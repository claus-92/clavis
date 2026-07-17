"""Textual screens and modals for the Clavis terminal interface."""
from __future__ import annotations

from typing import Any, Optional

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Input, Label, Static

from clavis.cli_utils import get_create_next_prompt
from clavis.client import ClavisClient


# Note: build_create_config lives in cli_utils and is used by CLI.
# TUI uses get_create_next_prompt + build_config_from_prompt_answers for step-by-step prompting.


class MessageModal(ModalScreen[None]):
    """Show a message until keypress."""

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="msg-dialog"):
                yield Label(self.message)
                yield Static("Press any key to continue")

    def on_key(self, event) -> None:  # type: ignore[override]
        self.dismiss()


class BoardDetailScreen(Screen[None]):
    """Full board detail view with scoped actions and editable parameters."""

    BINDINGS = [
        ("escape", "back", "Back"),
        ("r", "refresh", "Refresh"),
        ("c", "connect", "Connect"),
        ("d", "disconnect", "Disconnect"),
        ("o", "power_on", "Power on"),
        ("f", "power_off", "Power off"),
        ("s", "start_acquisition", "Start acquisition"),
        ("x", "stop_acquisition", "Stop acquisition"),
    ]

    def __init__(self, client: ClavisClient, board: dict[str, Any]) -> None:
        super().__init__()
        self.client = client
        self.board = board
        self.status: dict[str, Any] = {}
        self.parameters: dict[str, Any] = {}
        self._parameter_rows: list[dict[str, Any]] = []

    @property
    def board_id(self) -> str:
        return str(self.board.get("board_id", ""))

    def compose(self) -> ComposeResult:
        yield Static(id="detail-title", classes="detail-title")
        yield Static(id="detail-status", classes="detail-status")
        yield Static(
            "Actions:  (c) Connect  (d) Disconnect  (o) Power On  (f) Power Off  "
            "(s) Start Acquisition (x) Stop Acquisition  (r) Refresh  (Esc) Back",
            classes="detail-actions",
        )
        yield Static("Parameters: select a row and press Enter to edit", classes="detail-help")
        yield DataTable(id="parameters-table", zebra_stripes=True, cursor_type="row")
        yield Static(id="detail-message", classes="detail-message")

    def on_mount(self) -> None:
        table = self.query_one("#parameters-table", DataTable)
        table.add_columns("scope", "parameter", "current", "default", "options", "description")
        table.focus()
        self.refresh_detail()

    def action_back(self) -> None:
        self.dismiss(None)

    def action_refresh(self) -> None:
        self.refresh_detail("Refreshed")

    def action_connect(self) -> None:
        self._perform("connect")

    def action_disconnect(self) -> None:
        self._perform("disconnect")

    def action_power_on(self) -> None:
        self._perform("power-on")

    def action_power_off(self) -> None:
        self._perform("power-off")

    def action_start_acquisition(self) -> None:
        self._perform("start-acquisition")

    def action_stop_acquisition(self) -> None:
        self._perform("stop-acquisition")

    def refresh_detail(self, message: str = "") -> None:
        try:
            board = self.client.get_board(self.board_id)
            if isinstance(board, dict):
                self.board = {**self.board, **board}
        except Exception:
            pass
        try:
            status = self.client.get_board_status(self.board_id)
            self.status = status if isinstance(status, dict) else {}
        except Exception as exc:
            self.status = {}
            message = f"Status error: {exc}"
        try:
            parameters = self.client.get_parameters(self.board_id)
            self.parameters = parameters if isinstance(parameters, dict) else {}
        except Exception as exc:
            self.parameters = {"generalParameters": [], "groupParameters": [], "channelParameters": []}
            message = f"Parameter error: {exc}"
        self._render_detail(message)

    def _render_detail(self, message: str = "") -> None:
        self.query_one("#detail-title", Static).update(f"Board Detail: {self.board_id}")
        self.query_one("#detail-status", Static).update(self._render_status())
        self.query_one("#detail-message", Static).update(message)

        self._parameter_rows = self._build_parameter_rows()
        table = self.query_one("#parameters-table", DataTable)
        table.clear()
        for row in self._parameter_rows:
            table.add_row(
                row["scope"],
                row["name"],
                _format_value(row["current"]),
                _format_value(row["default"]),
                _format_options(row["options"]),
                row["description"],
            )

    def _render_status(self) -> str:
        return (
            f"Name       {self.board.get('name', '-')}\n"
            f"Type       {self.board.get('board_type', '-')}\n"
            f"ASIC       {self.board.get('asic', '-')}\n"
            f"FPGA       {self.board.get('fpga', '-')}\n"
            f"Firmware   {self.board.get('firmware_version', '-')}\n"
            f"Connected  {_yes_no(self.status.get('connected', False))}\n"
            f"Powered    {_yes_no(self.status.get('powered', False))}\n"
            f"Acquiring  {_yes_no(self.status.get('acquiring', False))}"
        )

    def _build_parameter_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        specs = [
            ("global", "generalParameters", self.status.get("global_options", {})),
            ("group", "groupParameters", self.status.get("group_options", {})),
            ("channel", "channelParameters", self.status.get("channel_options", {})),
        ]
        for scope, key, values in specs:
            definitions = self.parameters.get(key, [])
            if not isinstance(definitions, list):
                continue
            for definition in definitions:
                if isinstance(definition, dict):
                    row = dict(definition)
                else:
                    row = dict(getattr(definition, "model_dump", lambda: {})())
                row["scope"] = scope
                row["current"] = self._current_parameter_value(scope, row, values)
                row["default"] = row.get("defaultValue")
                row["options"] = row.get("options", [])
                row["description"] = row.get("description", "")
                rows.append(row)
        return rows

    def _current_parameter_value(self, scope: str, row: dict[str, Any], values: Any) -> Any:
        name = row.get("name")
        default = row.get("defaultValue")
        if scope == "global":
            return values.get(name, default) if isinstance(values, dict) else default
        if not isinstance(values, dict):
            return default
        configured = [f"{target}={opts[name]}" for target, opts in values.items() if isinstance(opts, dict) and name in opts]
        return ", ".join(configured) if configured else default

    def _perform(self, action: str) -> None:
        try:
            if action == "connect":
                self.client.connect_board(self.board_id)
            elif action == "disconnect":
                self.client.disconnect_board(self.board_id)
            elif action == "power-on":
                self.client.power_on(self.board_id)
            elif action == "power-off":
                self.client.power_off(self.board_id)
            elif action == "start-acquisition":
                self.client.start_acquisition(self.board_id)
            elif action == "stop-acquisition":
                self.client.stop_acquisition(self.board_id)
            self.refresh_detail(f"Applied: {action}")
        except Exception as exc:
            self.refresh_detail(f"Error: {exc}")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "parameters-table":
            return
        if event.cursor_row >= len(self._parameter_rows):
            return

        async def edit_parameter() -> None:
            row = self._parameter_rows[event.cursor_row]
            target_id = ""
            if row["scope"] in {"group", "channel"}:
                label = "Group ID" if row["scope"] == "group" else "Channel ID"
                target_id = await self.app.push_screen_wait(TextInputModal(label)) or ""
                if not target_id:
                    return
            opts = row.get("options") or []
            if opts:
                title = f"Select {row.get('scope')} parameter {row.get('name')}"
                value = await self.app.push_screen_wait(OptionsSelectModal(opts, title=title))
            else:
                value = await self.app.push_screen_wait(ParameterValueModal(row))
            if value is None:
                return
            try:
                parsed = _parse_parameter_value(value, row)
                if row["scope"] == "global":
                    self.client.set_global(self.board_id, {row["name"]: parsed})
                elif row["scope"] == "group":
                    self.client.set_group(self.board_id, target_id, {row["name"]: parsed})
                else:
                    self.client.set_channel(self.board_id, target_id, {row["name"]: parsed})
                self.refresh_detail(f"Set {row['scope']} parameter {row['name']}")
            except Exception as exc:
                self.refresh_detail(f"Set failed: {exc}")

        self.run_worker(edit_parameter())


class TextInputModal(ModalScreen[Optional[str]]):
    def __init__(self, title: str, default: str = "") -> None:
        super().__init__()
        self.title = title
        self.default = default

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="prompt-dialog"):
                yield Label(self.title)
                yield Input(value=self.default, id="prompt-input")
                yield Static("Enter: confirm   Esc: cancel")

    def on_mount(self) -> None:
        self.query_one("#prompt-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.dismiss(event.value.strip())

    def on_key(self, event) -> None:  # type: ignore[override]
        if event.key == "escape":
            event.stop()
            self.dismiss(None)


class ParameterValueModal(TextInputModal):
    def __init__(self, parameter: dict[str, Any]) -> None:
        self.parameter = parameter
        super().__init__(self._title())

    def _title(self) -> str:
        current = _format_value(self.parameter.get("current", ""))
        options = _format_options(self.parameter.get("options", []))
        current_part = f" Current: {current}." if current else ""
        suffix = f" Options: {options}" if options else ""
        return f"Set {self.parameter.get('scope')} parameter {self.parameter.get('name')}.{current_part}{suffix}"


class OptionsSelectModal(ModalScreen[Optional[Any]]):
    """Keyboard selection from a list of options."""

    def __init__(self, options: list[Any], title: str = "Select") -> None:
        super().__init__()
        self._options = list(options)
        self._title_text = title

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="select-dialog"):
                yield Label(self._title_text)
                yield DataTable(id="options-table", cursor_type="row", zebra_stripes=True)
                yield Static("↑↓ select  Enter: confirm  Esc: cancel")

    def on_mount(self) -> None:
        table = self.query_one("#options-table", DataTable)
        table.add_columns("value")
        for opt in self._options:
            table.add_row(_format_value(opt))
        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "options-table":
            return
        if event.cursor_row >= len(self._options):
            return
        chosen = self._options[event.cursor_row]
        self.dismiss(chosen)

    def on_key(self, event) -> None:  # type: ignore[override]
        if event.key == "escape":
            event.stop()
            self.dismiss(None)
            return


def _yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def _format_options(options: Any) -> str:
    if not isinstance(options, list):
        return ""
    return ", ".join(_format_value(option) for option in options)


def _parse_parameter_value(raw: str, parameter: dict[str, Any]) -> Any:
    value_type = parameter.get("type")
    if value_type == "integer":
        value: Any = int(raw)
    elif value_type == "number":
        value = float(raw)
    elif value_type == "boolean":
        lowered = raw.lower()
        if lowered in {"true", "yes", "y", "1"}:
            value = True
        elif lowered in {"false", "no", "n", "0"}:
            value = False
        else:
            raise ValueError("Expected a boolean value")
    else:
        value = raw
    options = parameter.get("options", [])
    if isinstance(options, list) and options and value not in options:
        allowed = ", ".join(_format_value(option) for option in options)
        raise ValueError(f"Value must be one of: {allowed}")
    return value


class CreateBoardScreen(ModalScreen[Optional[dict[str, Any]]]):
    """Interactive board creation using shared schema helpers."""

    def __init__(self, client: ClavisClient) -> None:
        super().__init__()
        self.client = client
        self._answers: list[str] = []

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="create-dialog"):
                yield Label("Create Board")
                yield Static("Follow prompts. Press Esc at any time to cancel.")
                yield Input(placeholder="answer", id="create-input")
                yield Static(id="create-status")

    def on_mount(self) -> None:
        self._start_create_flow()

    def _start_create_flow(self) -> None:
        inp = self.query_one("#create-input", Input)
        inp.focus()
        self._ask_next()

    def _ask(self, question: str) -> None:
        status = self.query_one("#create-status", Static)
        status.update(question)
        inp = self.query_one("#create-input", Input)
        inp.value = ""
        inp.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        answer = event.value.strip()
        if answer:
            self._answers.append(answer)
        event.stop()
        self._ask_next()

    def _ask_next(self) -> None:
        """Ask the next question or complete using the single shared prompt driver."""
        try:
            board_types = self.client.list_board_types() or []
            question, config = get_create_next_prompt(self._answers, board_types)
            if config is not None:
                self.dismiss(config)
                return
            if question is not None:
                if not self._answers:
                    board_type_options = [
                        bt.get("board_type")
                        for bt in board_types
                        if isinstance(bt, dict) and bt.get("board_type")
                    ]
                    self.app.push_screen(
                        OptionsSelectModal(
                            sorted(board_type_options),
                            title="Select board type",
                        ),
                        self._on_board_type_selected,
                    )
                else:
                    self._ask(question)
            else:
                self._ask("Provide value")
        except Exception as exc:
            self.query_one("#create-status", Static).update(f"Error: {exc}")

    def _on_board_type_selected(self, board_type: str | None) -> None:
        if board_type:
            self._answers.append(board_type)
        self._ask_next()

    def on_key(self, event) -> None:  # type: ignore[override]
        if event.key == "escape":
            self.dismiss(None)
            return

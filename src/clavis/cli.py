from pathlib import Path
from typing import Any, Optional

import httpx
import typer

from clavis.branding import about_text, version_text
from clavis.client import ClavisClient
from clavis.runtime import DEFAULT_UDS
from clavis.cli_utils import (
    build_create_config,
    format_result,
    parse_options,
    parse_schema_value,
)

app = typer.Typer(
    help="Control clavisd through its REST API. Use --help on any command for details.",
    add_completion=True,
)
boards_app = typer.Typer(help="Board management and control commands.")
app.add_typer(boards_app, name="boards")
config_app = typer.Typer(help="Dump or load the full system configuration.")
app.add_typer(config_app, name="config")


class AppState:
    host: Optional[str] = None
    uds: str = DEFAULT_UDS


app_state = AppState()


def client() -> ClavisClient:
    return ClavisClient(host=app_state.host, uds=app_state.uds)


def format_http_error(exc: httpx.HTTPError) -> str:
    if app_state.host is None and isinstance(exc, httpx.ConnectError):
        return (
            f"Could not connect to clavisd at Unix socket {app_state.uds}. "
            f"Start it with: uv run clavisd --uds {app_state.uds}"
        )
    detail = getattr(exc, "detail", None)
    if not detail and isinstance(exc, httpx.HTTPStatusError):
        try:
            data = exc.response.json()
            if isinstance(data, dict):
                d = data.get("detail")
                if isinstance(d, str):
                    detail = d
        except Exception:
            pass
    if detail:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status is not None:
            return f"HTTP error: {detail} (HTTP {status})"
        return f"HTTP error: {detail}"
    return f"HTTP error: {exc}"


def echo_result(result: Any) -> None:
    typer.echo(format_result(result))


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(version_text())
        raise typer.Exit()


@app.callback()
def main(
    host: Optional[str] = typer.Option(
        None,
        "--host",
        envvar="CLAVIS_HOST",
        help="Remote HTTP/HTTPS daemon URL.",
    ),
    uds: str = typer.Option(DEFAULT_UDS, "--uds", envvar="CLAVIS_UDS", help="Local Unix socket path."),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the installed Clavis version and exit.",
    ),
) -> None:
    """Global options for connecting to the daemon."""
    app_state.host = host
    app_state.uds = uds


@app.command()
def about() -> None:
    """Show Clavis project and version information."""
    typer.echo(about_text())


@app.command()
def status() -> None:
    """Show the current status of the clavisd daemon."""
    try:
        result = client().status()
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@app.command()
def tui() -> None:
    """Launch the interactive Textual TUI (live board status dashboard)."""
    from clavis.tui.app import run_tui

    run_tui(host=app_state.host, uds=app_state.uds)


@boards_app.command("types")
def boards_types() -> None:
    """List registered board types and their JSON config schemas."""
    try:
        result = client().list_board_types()
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("list")
def boards_list() -> None:
    """List all configured boards."""
    try:
        result = client().list_boards()
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("create")
def boards_create(
    options: list[str] = typer.Argument(
        default_factory=list,
        help="Optional KEY=VALUE pairs. Missing required fields will be prompted interactively.",
    ),
) -> None:
    """Create a new board from its configuration.

    Example:
        clavis boards create board_type=samidare board_id=dev-01 name=MyBoard host=192.168.0.10
    """
    try:
        cfg = build_create_config(options, client())
        result = client().create_board(cfg)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("get")
def boards_get(
    board_id: str = typer.Argument(..., help="Board identifier"),
) -> None:
    """Get metadata for a specific board."""
    try:
        result = client().get_board(board_id)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("config")
def boards_config(
    board_id: str = typer.Argument(..., help="Board identifier"),
) -> None:
    """Show the stored configuration for a board."""
    try:
        result = client().get_board_config(board_id)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("connect")
def boards_connect(
    board_id: str = typer.Argument(..., help="Board identifier"),
) -> None:
    """Connect to the board (establish transport/client)."""
    try:
        result = client().connect_board(board_id)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("disconnect")
def boards_disconnect(
    board_id: str = typer.Argument(..., help="Board identifier"),
) -> None:
    """Disconnect from the board."""
    try:
        result = client().disconnect_board(board_id)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("power-on")
def boards_power_on(
    board_id: str = typer.Argument(..., help="Board identifier"),
) -> None:
    """Power on the board."""
    try:
        result = client().power_on(board_id)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("power-off")
def boards_power_off(
    board_id: str = typer.Argument(..., help="Board identifier"),
) -> None:
    """Power off the board."""
    try:
        result = client().power_off(board_id)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("start-acquisition")
def boards_start_acquisition(
    board_id: str = typer.Argument(..., help="Board identifier"),
) -> None:
    """Start data acquisition on the board."""
    try:
        result = client().start_acquisition(board_id)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("arm-acquisition")
def boards_arm_acquisition(
    board_id: str = typer.Argument(..., help="Board identifier"),
) -> None:
    """Arm the board and wait for a start request."""
    try:
        result = client().arm_acquisition(board_id)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("stop-acquisition")
def boards_stop_acquisition(
    board_id: str = typer.Argument(..., help="Board identifier"),
) -> None:
    """Stop data acquisition on the board."""
    try:
        result = client().stop_acquisition(board_id)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("parameters")
def boards_parameters(
    board_id: str = typer.Argument(..., help="Board identifier"),
) -> None:
    """Show the parameter definitions (general, group, channel) for a board."""
    try:
        result = client().get_parameters(board_id)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("set-global")
def boards_set_global(
    board_id: str = typer.Argument(..., help="Board identifier"),
    options: list[str] = typer.Argument(
        ..., help="One or more KEY=VALUE pairs, e.g. gain=2 enabled=true"
    ),
) -> None:
    """Set global (board-wide) parameters.

    Example:
        clavis boards set-global dev-001 gain=2 power=true
    """
    opts = parse_options(options)
    try:
        result = client().set_global(board_id, opts)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("set-group")
def boards_set_group(
    board_id: str = typer.Argument(..., help="Board identifier"),
    group_id: str = typer.Argument(..., help="Group identifier (e.g. 0, 1, A)"),
    options: list[str] = typer.Argument(
        ..., help="One or more KEY=VALUE pairs for the group"
    ),
) -> None:
    """Set parameters for a specific parameter group.

    Example:
        clavis boards set-group dev-001 0 gain=1
    """
    opts = parse_options(options)
    try:
        result = client().set_group(board_id, group_id, opts)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("set-channel")
def boards_set_channel(
    board_id: str = typer.Argument(..., help="Board identifier"),
    channel_id: str = typer.Argument(..., help="Channel identifier (e.g. 0, 1, 2)"),
    options: list[str] = typer.Argument(
        ..., help="One or more KEY=VALUE pairs for the channel"
    ),
) -> None:
    """Set parameters for a specific channel.

    Example:
        clavis boards set-channel dev-001 0 gain=3 offset=10
    """
    opts = parse_options(options)
    try:
        result = client().set_channel(board_id, channel_id, opts)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@boards_app.command("status")
def boards_status(
    board_id: str = typer.Argument(..., help="Board identifier"),
) -> None:
    """Show runtime status for a board (connected, powered, acquiring, options)."""
    try:
        result = client().get_board_status(board_id)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)


@config_app.command("dump")
def config_dump(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write to file instead of stdout."),
) -> None:
    """Dump the full system configuration (boards + current parameters) to stdout or a file."""
    try:
        result = client().get_config()
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    text = format_result(result)
    if output is not None:
        output.write_text(text + "\n")
        typer.echo(f"Configuration written to {output}", err=True)
    else:
        typer.echo(text)


@config_app.command("load")
def config_load(
    input: Path = typer.Argument(..., help="JSON file with the system configuration to apply."),
) -> None:
    """Load and apply a full system configuration from a JSON file."""
    import json

    try:
        data = json.loads(input.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise typer.BadParameter(f"Failed to read config file: {exc}") from exc
    try:
        result = client().apply_config(data)
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    echo_result(result)

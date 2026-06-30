import shlex
from typing import Optional

import httpx
import typer

from clavis.client.http import ClavisClient
from clavis.cli.commands import COMMAND_HELP, CommandError, dispatch_command

DEFAULT_UDS = "/tmp/clavisd.sock"

app = typer.Typer(help="Control clavisd through its REST API.")
boards_app = typer.Typer(help="Board commands.")
app.add_typer(boards_app, name="boards")


def client() -> ClavisClient:
    return ClavisClient(host=app_state.host, uds=app_state.uds)


def echo_command(args: list[str]) -> None:
    try:
        result = dispatch_command(args, client())
    except CommandError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if result is not None:
        typer.echo(result)


class AppState:
    host: Optional[str] = None
    uds: str = DEFAULT_UDS


app_state = AppState()


@app.callback()
def main(
    host: Optional[str] = typer.Option(None, help="Remote HTTP/HTTPS daemon URL."),
    uds: str = typer.Option(DEFAULT_UDS, help="Local Unix socket path."),
) -> None:
    app_state.host = host
    app_state.uds = uds


@app.command()
def status() -> None:
    echo_command(["status"])


@app.command()
def shell() -> None:
    typer.echo("clavis shell. Type 'help' for commands, 'exit' to quit.")
    shell_client = client()
    try:
        while True:
            try:
                line = input("clavis> ")
            except EOFError:
                typer.echo()
                break

            try:
                args = shlex.split(line)
            except ValueError as exc:
                typer.echo(f"Error: {exc}", err=True)
                continue

            if not args:
                continue
            if args in (["exit"], ["quit"]):
                break

            try:
                result = dispatch_command(args, shell_client)
            except CommandError as exc:
                typer.echo(f"Error: {exc}", err=True)
                typer.echo(COMMAND_HELP.rstrip())
                continue
            except httpx.HTTPError as exc:
                typer.echo(f"HTTP error: {exc}", err=True)
                continue

            if result is not None:
                typer.echo(result)
    finally:
        shell_client.close()


@boards_app.command("discover")
def boards_discover() -> None:
    echo_command(["boards", "discover"])


@boards_app.command("list")
def boards_list() -> None:
    echo_command(["boards", "list"])


@boards_app.command("get")
def boards_get(board_id: str) -> None:
    echo_command(["boards", "get", board_id])


@boards_app.command("connect")
def boards_connect(board_id: str) -> None:
    echo_command(["boards", "connect", board_id])


@boards_app.command("disconnect")
def boards_disconnect(board_id: str) -> None:
    echo_command(["boards", "disconnect", board_id])


@boards_app.command("power-on")
def boards_power_on(board_id: str) -> None:
    echo_command(["boards", "power-on", board_id])


@boards_app.command("power-off")
def boards_power_off(board_id: str) -> None:
    echo_command(["boards", "power-off", board_id])


@boards_app.command("parameters")
def boards_parameters(board_id: str) -> None:
    echo_command(["boards", "parameters", board_id])


@boards_app.command("set-global")
def boards_set_global(board_id: str, options: list[str]) -> None:
    echo_command(["boards", "set-global", board_id, *options])


@boards_app.command("set-group")
def boards_set_group(board_id: str, group_id: str, options: list[str]) -> None:
    echo_command(["boards", "set-group", board_id, group_id, *options])


@boards_app.command("set-channel")
def boards_set_channel(board_id: str, channel_id: str, options: list[str]) -> None:
    echo_command(["boards", "set-channel", board_id, channel_id, *options])


@boards_app.command("status")
def boards_status(board_id: str) -> None:
    echo_command(["boards", "status", board_id])

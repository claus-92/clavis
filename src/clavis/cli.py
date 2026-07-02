import json
import shlex
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

import httpx
import typer

from clavis.client import ClavisClient

DEFAULT_UDS = "/tmp/clavisd.sock"

app = typer.Typer(help="Control clavisd through its REST API.")
boards_app = typer.Typer(help="Board commands.")
app.add_typer(boards_app, name="boards")


class CommandError(ValueError):
    pass


COMMAND_HELP = """Commands:
  status
  boards discover
  boards types
  boards list
  boards create [KEY=VALUE...]
  boards get BOARD_ID
  boards config BOARD_ID
  boards connect BOARD_ID
  boards disconnect BOARD_ID
  boards power-on BOARD_ID
  boards power-off BOARD_ID
  boards start-acquisition BOARD_ID
  boards stop-acquisition BOARD_ID
  boards parameters BOARD_ID
  boards set-global BOARD_ID KEY=VALUE...
  boards set-group BOARD_ID GROUP_ID KEY=VALUE...
  boards set-channel BOARD_ID CHANNEL_ID KEY=VALUE...
  boards status BOARD_ID
  help
  exit | quit
"""


class AppState:
    host: Optional[str] = None
    uds: str = DEFAULT_UDS


app_state = AppState()


def client() -> ClavisClient:
    return ClavisClient(host=app_state.host, uds=app_state.uds)


def format_http_error(exc: httpx.HTTPError) -> str:
    if app_state.host is None and isinstance(exc, httpx.ConnectError):
        return f"Could not connect to clavisd at Unix socket {app_state.uds}. Start it with: uv run clavisd --uds {app_state.uds}"
    return f"HTTP error: {exc}"


def parse_options(values: list[str]) -> dict[str, object]:
    options: dict[str, object] = {}
    for value in values:
        if "=" not in value:
            raise CommandError("Options must be KEY=VALUE")
        key, raw = value.split("=", 1)
        if raw.isdigit():
            options[key] = int(raw)
        elif raw.lower() in {"true", "false"}:
            options[key] = raw.lower() == "true"
        else:
            options[key] = raw
    return options


PromptFunc = Callable[[str], str]


def parse_schema_value(raw: str, schema: dict[str, Any]) -> object:
    value_type = schema.get("type")
    if value_type == "integer":
        return int(raw)
    if value_type == "number":
        return float(raw)
    if value_type == "boolean":
        lowered = raw.lower()
        if lowered in {"true", "yes", "y", "1"}:
            return True
        if lowered in {"false", "no", "n", "0"}:
            return False
        raise CommandError(f"Expected boolean value for {schema.get('title', 'field')}")
    return raw


def build_create_config(options: list[str], client: ClavisClient, prompt: PromptFunc = typer.prompt) -> dict[str, object]:
    config = parse_options(options)
    board_types = client.list_board_types()
    if not isinstance(board_types, list):
        raise CommandError("Daemon returned invalid board type information")

    type_map = {item.get("board_type"): item for item in board_types if isinstance(item, dict)}
    if not type_map:
        raise CommandError("No board types are available")

    if "board_type" not in config:
        available = ", ".join(sorted(str(board_type) for board_type in type_map))
        config["board_type"] = prompt(f"Board type ({available})")

    board_type = str(config["board_type"])
    type_info = type_map.get(board_type)
    if type_info is None:
        available = ", ".join(sorted(str(board_type) for board_type in type_map))
        raise CommandError(f"Unknown board type: {board_type}. Available types: {available}")

    schema = type_info.get("config_schema", {})
    if not isinstance(schema, dict):
        raise CommandError(f"Board type has invalid config schema: {board_type}")

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        properties = {}
    required_fields = schema.get("required", [])
    if not isinstance(required_fields, list):
        required_fields = []

    for field in required_fields:
        if field in config:
            continue
        field_schema = properties.get(field, {})
        if not isinstance(field_schema, dict):
            field_schema = {}
        title = field_schema.get("title") or humanize_key(str(field))
        config[str(field)] = parse_schema_value(prompt(str(title)), field_schema)

    return config


def dispatch_command(args: list[str], client: ClavisClient, prompt: PromptFunc = typer.prompt) -> Any:
    match args:
        case ["status"]:
            return client.status()
        case ["boards", "discover"]:
            return client.discover_boards()
        case ["boards", "types"]:
            return client.list_board_types()
        case ["boards", "list"]:
            return client.list_boards()
        case ["boards", "create", *options]:
            return client.create_board(build_create_config(options, client, prompt))
        case ["boards", "get", board_id]:
            return client.get_board(board_id)
        case ["boards", "config", board_id]:
            return client.get_board_config(board_id)
        case ["boards", "connect", board_id]:
            return client.connect_board(board_id)
        case ["boards", "disconnect", board_id]:
            return client.disconnect_board(board_id)
        case ["boards", "power-on", board_id]:
            return client.power_on(board_id)
        case ["boards", "power-off", board_id]:
            return client.power_off(board_id)
        case ["boards", "start-acquisition", board_id]:
            return client.start_acquisition(board_id)
        case ["boards", "stop-acquisition", board_id]:
            return client.stop_acquisition(board_id)
        case ["boards", "parameters", board_id]:
            return client.get_parameters(board_id)
        case ["boards", "set-global", board_id, *options]:
            return client.set_global(board_id, parse_options(options))
        case ["boards", "set-group", board_id, group_id, *options]:
            return client.set_group(board_id, group_id, parse_options(options))
        case ["boards", "set-channel", board_id, channel_id, *options]:
            return client.set_channel(board_id, channel_id, parse_options(options))
        case ["boards", "status", board_id]:
            return client.get_board_status(board_id)
        case ["help"]:
            return COMMAND_HELP.rstrip()
        case []:
            return None
        case _:
            raise CommandError(f"Unknown command: {' '.join(args)}")


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(format_value(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, indent=2, sort_keys=True)
    return str(value)


def humanize_key(key: str) -> str:
    result = ""
    for char in key:
        if char.isupper() and result:
            result += " "
        result += char
    return result.replace("_", " ").title()


def format_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return "No results."

    rendered_rows = [[format_value(row.get(key, "")) for key, _ in columns] for row in rows]
    widths = [len(label) for _, label in columns]
    for row in rendered_rows:
        widths = [max(width, len(value)) for width, value in zip(widths, row)]

    header = "  ".join(label.ljust(width) for width, (_, label) in zip(widths, columns)).rstrip()
    separator = "  ".join("-" * width for width in widths).rstrip()
    lines = [header, separator]
    lines.extend("  ".join(value.ljust(width) for width, value in zip(widths, row)).rstrip() for row in rendered_rows)
    return "\n".join(lines)


def format_key_values(data: dict[str, Any]) -> str:
    simple_items = [(key, value) for key, value in data.items() if not isinstance(value, (dict, list))]
    nested_items = [(key, value) for key, value in data.items() if isinstance(value, (dict, list))]
    width = max((len(humanize_key(key)) for key, _ in simple_items), default=0)
    lines = [f"{humanize_key(key).ljust(width)}  {format_value(value)}".rstrip() for key, value in simple_items]

    for key, value in nested_items:
        if lines:
            lines.append("")
        lines.append(f"{humanize_key(key)}:")
        lines.append(format_value(value))

    return "\n".join(lines)


def format_parameters(data: dict[str, Any]) -> str:
    sections = [
        ("General Parameters", data.get("generalParameters", [])),
        ("Channel Parameters", data.get("channelParameters", [])),
        ("Group Parameters", data.get("groupParameters", [])),
    ]
    columns = [
        ("name", "name"),
        ("type", "type"),
        ("defaultValue", "default"),
        ("options", "options"),
        ("description", "description"),
    ]
    lines: list[str] = []
    for title, rows in sections:
        if lines:
            lines.append("")
        lines.append(title)
        lines.append(format_table(rows, columns) if rows else "No parameters.")
    return "\n".join(lines)


def format_result(result: Any) -> str:
    if isinstance(result, dict) and {"generalParameters", "channelParameters", "groupParameters"}.issubset(result):
        return format_parameters(result)
    if isinstance(result, dict):
        return format_key_values(result)
    if isinstance(result, list):
        if not result:
            return "No results."
        if all(isinstance(item, dict) for item in result):
            keys = list(dict.fromkeys(key for item in result for key in item.keys()))
            columns = [(key, key) for key in keys if key != "config_schema"]
            table = format_table(result, columns)
            if any("config_schema" in item for item in result):
                details = []
                for item in result:
                    schema = item.get("config_schema")
                    if schema is None:
                        continue
                    board_type = item.get("board_type", "unknown")
                    details.append(f"\nConfig schema for {board_type}:\n{json.dumps(schema, indent=2, sort_keys=True)}")
                return table + "\n" + "\n".join(details)
            return table
        return "\n".join(format_value(item) for item in result)
    return format_value(result)


def echo_result(result: Any) -> None:
    typer.echo(format_result(result))


def echo_command(args: list[str]) -> None:
    try:
        result = dispatch_command(args, client())
    except CommandError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except httpx.HTTPError as exc:
        raise typer.BadParameter(format_http_error(exc)) from exc
    if result is not None:
        echo_result(result)


def setup_shell_history(history_path: Path | None = None) -> None:
    try:
        import atexit
        import readline
    except ImportError:
        return

    path = history_path or Path.home() / ".clavis_history"
    try:
        readline.read_history_file(str(path))
    except FileNotFoundError:
        pass
    except OSError:
        pass

    readline.set_history_length(1000)

    def write_history() -> None:
        try:
            readline.write_history_file(str(path))
        except OSError:
            pass

    atexit.register(write_history)


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
    setup_shell_history()
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
                typer.echo(format_http_error(exc), err=True)
                continue

            if result is not None:
                echo_result(result)
    finally:
        shell_client.close()


@boards_app.command("discover")
def boards_discover() -> None:
    echo_command(["boards", "discover"])


@boards_app.command("list")
def boards_list() -> None:
    echo_command(["boards", "list"])


@boards_app.command("types")
def boards_types() -> None:
    echo_command(["boards", "types"])


@boards_app.command("create")
def boards_create(options: list[str]) -> None:
    echo_command(["boards", "create", *options])


@boards_app.command("get")
def boards_get(board_id: str) -> None:
    echo_command(["boards", "get", board_id])


@boards_app.command("config")
def boards_config(board_id: str) -> None:
    echo_command(["boards", "config", board_id])


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


@boards_app.command("start-acquisition")
def boards_start_acquisition(board_id: str) -> None:
    echo_command(["boards", "start-acquisition", board_id])


@boards_app.command("stop-acquisition")
def boards_stop_acquisition(board_id: str) -> None:
    echo_command(["boards", "stop-acquisition", board_id])


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

from typing import Any

from clavis.client.http import ClavisClient


class CommandError(ValueError):
    pass


COMMAND_HELP = """Commands:
  status
  boards discover
  boards list
  boards get BOARD_ID
  boards connect BOARD_ID
  boards disconnect BOARD_ID
  boards power-on BOARD_ID
  boards power-off BOARD_ID
  boards parameters BOARD_ID
  boards set-global BOARD_ID KEY=VALUE...
  boards set-group BOARD_ID GROUP_ID KEY=VALUE...
  boards set-channel BOARD_ID CHANNEL_ID KEY=VALUE...
  boards status BOARD_ID
  help
  exit | quit
"""


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


def dispatch_command(args: list[str], client: ClavisClient) -> Any:
    match args:
        case ["status"]:
            return client.status()
        case ["boards", "discover"]:
            return client.discover_boards()
        case ["boards", "list"]:
            return client.list_boards()
        case ["boards", "get", board_id]:
            return client.get_board(board_id)
        case ["boards", "connect", board_id]:
            return client.connect_board(board_id)
        case ["boards", "disconnect", board_id]:
            return client.disconnect_board(board_id)
        case ["boards", "power-on", board_id]:
            return client.power_on(board_id)
        case ["boards", "power-off", board_id]:
            return client.power_off(board_id)
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

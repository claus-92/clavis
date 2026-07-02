#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s BOARD_NAME [OUTPUT_DIR]\n' "$(basename "$0")" >&2
  printf 'Example: %s my-board ../clavis-my-board\n' "$(basename "$0")" >&2
}

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  usage
  exit 2
fi

board_name="$1"
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

slug="$(printf '%s' "$board_name" | tr '[:upper:]' '[:lower:]' | tr -c '[:alnum:]' '-' | sed 's/^-*//; s/-*$//; s/--*/-/g')"
module_name="clavis_$(printf '%s' "$slug" | tr '-' '_')"

if [ -z "$slug" ]; then
  printf 'Error: BOARD_NAME must contain at least one letter or number.\n' >&2
  exit 2
fi

output_dir="${2:-"$script_dir/../clavis-$slug"}"
project_name="clavis-$slug"

if [ -e "$output_dir" ]; then
  printf 'Error: output path already exists: %s\n' "$output_dir" >&2
  exit 1
fi

mkdir -p "$output_dir/src/$module_name/parameter_definitions"

cat > "$output_dir/pyproject.toml" <<EOF
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "$project_name"
version = "0.1.0"
description = "Clavis board plugin for $board_name"
requires-python = ">=3.10"
dependencies = ["clavis"]

[project.entry-points."clavis.boards"]
$slug = "$module_name:plugin"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
$module_name = ["parameter_definitions/*.json"]
EOF

cat > "$output_dir/README.md" <<EOF
# $project_name

Minimal Clavis board plugin for $slug.

The parameter_definitions/$slug.json file defines the parameters accepted by
set-global, set-group, and set-channel requests.

Install locally from the clavis core package directory:

    uv pip install -e ../$project_name

Restart clavisd, then verify:

    uv run clavis boards types
EOF

cat > "$output_dir/src/$module_name/parameter_definitions/$slug.json" <<EOF
{
  "generalParameters": [],
  "channelParameters": [],
  "groupParameters": []
}
EOF

cat > "$output_dir/src/$module_name/__init__.py" <<EOF
import json
from typing import Any
from importlib.resources import files

from pydantic import BaseModel

from clavis.boards.base import AcquisitionBoard
from clavis.clients.registry import ClientRegistry
from clavis.core.errors import BoardAlreadyAcquiringError, BoardAlreadyConnectedError, BoardNotAcquiringError, BoardNotConnectedError, BoardNotPoweredError
from clavis.plugins import BoardPlugin
from clavis.schemas import BoardMetadata, BoardStatus, ParameterDefinitions


class Config(BaseModel):
    board_id: str
    board_type: str = "$slug"
    name: str
    asic: str = "unknown"
    fpga: str = "unknown"
    firmware_version: str = "unknown"


class Board(AcquisitionBoard):
    def __init__(self, metadata: BoardMetadata) -> None:
        self.metadata = metadata
        self.connected = False
        self.powered = False
        self.acquiring = False
        self.global_options: dict[str, Any] = {}
        self.group_options: dict[str, dict[str, Any]] = {}
        self.channel_options: dict[str, dict[str, Any]] = {}

    def connect(self) -> None:
        if self.connected:
            raise BoardAlreadyConnectedError(f"Board already connected: {self.get_id()}")
        self.connected = True

    def disconnect(self) -> None:
        self._require_connected()
        self.connected = False
        self.powered = False
        self.acquiring = False

    def power_on(self) -> None:
        self._require_connected()
        self.powered = True

    def power_off(self) -> None:
        self._require_connected()
        self.powered = False
        self.acquiring = False

    def start_acquisition(self) -> None:
        self._require_connected()
        if not self.powered:
            raise BoardNotPoweredError(f"Board is not powered: {self.get_id()}")
        if self.acquiring:
            raise BoardAlreadyAcquiringError(f"Board is already acquiring: {self.get_id()}")
        self.acquiring = True

    def stop_acquisition(self) -> None:
        self._require_connected()
        if not self.acquiring:
            raise BoardNotAcquiringError(f"Board is not acquiring: {self.get_id()}")
        self.acquiring = False

    def set_global(self, options: dict[str, Any]) -> None:
        self._require_connected()
        self.global_options.update(options)

    def set_group(self, group_id: str, options: dict[str, Any]) -> None:
        self._require_connected()
        self.group_options.setdefault(group_id, {}).update(options)

    def set_channel(self, channel_id: str, options: dict[str, Any]) -> None:
        self._require_connected()
        self.channel_options.setdefault(channel_id, {}).update(options)

    def get_id(self) -> str:
        return self.metadata.board_id

    def get_status(self) -> BoardStatus:
        return BoardStatus(
            board_id=self.get_id(),
            connected=self.connected,
            powered=self.powered,
            acquiring=self.acquiring,
            global_options=self.global_options,
            group_options=self.group_options,
            channel_options=self.channel_options,
        )

    def _require_connected(self) -> None:
        if not self.connected:
            raise BoardNotConnectedError(f"Board not connected: {self.get_id()}")


def create_board(config: BaseModel, clients: ClientRegistry) -> Board:
    del clients
    data = config.model_dump() if hasattr(config, "model_dump") else config.dict()
    board_config = Config(**data)
    metadata = BoardMetadata(
        board_id=board_config.board_id,
        name=board_config.name,
        asic=board_config.asic,
        fpga=board_config.fpga,
        firmware_version=board_config.firmware_version,
        board_type="$slug",
    )
    return Board(metadata)


def load_parameters() -> ParameterDefinitions:
    path = files("$module_name") / "parameter_definitions" / "$slug.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if hasattr(ParameterDefinitions, "model_validate"):
        return ParameterDefinitions.model_validate(data)
    return ParameterDefinitions.parse_obj(data)


def plugin() -> BoardPlugin:
    return BoardPlugin(
        board_type="$slug",
        display_name="$board_name",
        config_model=Config,
        create_board=create_board,
        load_parameters=load_parameters,
    )
EOF

printf 'Created %s\n' "$output_dir"
printf 'Install from %s with: uv pip install -e %s\n' "$script_dir" "$output_dir"

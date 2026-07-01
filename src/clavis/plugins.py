from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any

from pydantic import BaseModel

from clavis.boards.base import AcquisitionBoard
from clavis.clients.registry import ClientRegistry
from clavis.schemas import ParameterDefinitions


CreateBoard = Callable[[BaseModel, ClientRegistry], AcquisitionBoard]
LoadParameters = Callable[[], ParameterDefinitions]


@dataclass(frozen=True)
class BoardPlugin:
    board_type: str
    display_name: str
    config_model: type[BaseModel]
    create_board: CreateBoard
    load_parameters: LoadParameters | None = None

    def config_schema(self) -> dict[str, Any]:
        if hasattr(self.config_model, "model_json_schema"):
            return self.config_model.model_json_schema()
        return self.config_model.schema()


class BoardPluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, BoardPlugin] = {}

    def register(self, plugin: BoardPlugin) -> None:
        self._plugins[plugin.board_type] = plugin

    def get(self, board_type: str) -> BoardPlugin:
        try:
            return self._plugins[board_type]
        except KeyError as exc:
            raise ValueError(f"Unknown board type: {board_type}") from exc

    def all(self) -> list[BoardPlugin]:
        return list(self._plugins.values())


def load_entry_point_plugins() -> list[BoardPlugin]:
    plugins: list[BoardPlugin] = []
    for entry_point in entry_points(group="clavis.boards"):
        plugins.append(entry_point.load()())
    return plugins

from pydantic import BaseModel

from clavis.boards.base import AcquisitionBoard
from clavis.clients.registry import ClientRegistry
from clavis.plugins import BoardPluginRegistry
from clavis.schemas import BoardConfig


class BoardFactory:
    def __init__(self, plugins: BoardPluginRegistry, clients: ClientRegistry) -> None:
        self.plugins = plugins
        self.clients = clients

    def create(self, config: BoardConfig | BaseModel | dict[str, object]) -> AcquisitionBoard:
        base_config = self._validate(BoardConfig, config)
        plugin = self.plugins.get(base_config.board_type)
        plugin_config = self._validate(plugin.config_model, base_config.model_dump() if hasattr(base_config, "model_dump") else base_config.dict())
        return plugin.create_board(plugin_config, self.clients)

    def _validate(self, model: type[BaseModel], data: BaseModel | dict[str, object]) -> BaseModel:
        if isinstance(data, model):
            return data
        if isinstance(data, BaseModel):
            if hasattr(data, "model_dump"):
                data = data.model_dump()
            else:
                data = data.dict()
        if hasattr(model, "model_validate"):
            return model.model_validate(data)
        return model.parse_obj(data)

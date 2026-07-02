from typing import Any

from clavis.boards.fake_plugin import plugin as fake_board_plugin
from clavis.clients.registry import ClientRegistry
from clavis.core.errors import InvalidBoardConfigurationError
from clavis.core.factory import BoardFactory
from clavis.core.registry import BoardRegistry
from clavis.parameters.validation import validate_options
from clavis.plugins import BoardPluginRegistry, load_entry_point_plugins
from clavis.schemas import BoardConfig, BoardMetadata, BoardStatus, BoardTypeInfo, ParameterDefinitions


class ClavisService:
    def __init__(self) -> None:
        self.registry = BoardRegistry()
        self.board_configs: dict[str, BoardConfig] = {}
        self.plugins = BoardPluginRegistry()
        self.plugins.register(fake_board_plugin())
        for plugin in load_entry_point_plugins():
            self.plugins.register(plugin)
        self.factory = BoardFactory(self.plugins, ClientRegistry())
        self.discover_boards()

    def discover_boards(self) -> list[BoardMetadata]:
        for config in [
            BoardConfig(board_id="dev-001", board_type="fake", name="Fake Board_TPC_1", asic="SAMPA_v4", fpga="Artix_Ultrascale_Plus", firmware_version="FW_v_1_2_3"),
            BoardConfig(board_id="dev-002", board_type="fake", name="Fake Board_TPC_2", asic="SAMPA_v4", fpga="Artix_Ultrascale_Plus", firmware_version="FW_v_1_2_3"),
        ]:
            if config.board_id not in {board.get_id() for board in self.registry.all()}:
                self.create_board(config)
        return self.list_boards()

    def list_board_types(self) -> list[BoardTypeInfo]:
        return [
            BoardTypeInfo(board_type=plugin.board_type, display_name=plugin.display_name, config_schema=plugin.config_schema())
            for plugin in self.plugins.all()
        ]

    def create_board(self, config: BoardConfig) -> BoardMetadata:
        try:
            board = self.factory.create(config)
        except ValueError as exc:
            raise InvalidBoardConfigurationError(str(exc)) from exc
        self.registry.add(board)
        self.board_configs[board.get_id()] = config
        return board.metadata

    def get_board_config(self, board_id: str) -> BoardConfig:
        self.registry.get(board_id)
        return self.board_configs[board_id]

    def delete_board(self, board_id: str) -> None:
        self.registry.remove(board_id)
        self.board_configs.pop(board_id, None)

    def list_boards(self) -> list[BoardMetadata]:
        return [board.metadata for board in self.registry.all()]

    def get_board(self, board_id: str) -> BoardMetadata:
        return self.registry.get(board_id).metadata

    def get_board_status(self, board_id: str) -> BoardStatus:
        return self.registry.get(board_id).get_status()

    def get_board_parameters(self, board_id: str) -> ParameterDefinitions:
        config = self.get_board_config(board_id)
        plugin = self.plugins.get(config.board_type)
        if plugin.load_parameters is None:
            raise InvalidBoardConfigurationError(f"Board type has no parameter definitions: {config.board_type}")
        return plugin.load_parameters()

    def connect_board(self, board_id: str) -> BoardStatus:
        board = self.registry.get(board_id)
        board.connect()
        return board.get_status()

    def disconnect_board(self, board_id: str) -> BoardStatus:
        board = self.registry.get(board_id)
        board.disconnect()
        return board.get_status()

    def power_on(self, board_id: str) -> BoardStatus:
        board = self.registry.get(board_id)
        board.power_on()
        return board.get_status()

    def power_off(self, board_id: str) -> BoardStatus:
        board = self.registry.get(board_id)
        board.power_off()
        return board.get_status()

    def start_acquisition(self, board_id: str) -> BoardStatus:
        board = self.registry.get(board_id)
        board.start_acquisition()
        return board.get_status()

    def stop_acquisition(self, board_id: str) -> BoardStatus:
        board = self.registry.get(board_id)
        board.stop_acquisition()
        return board.get_status()

    def set_global(self, board_id: str, options: dict[str, Any]) -> BoardStatus:
        parameters = self.get_board_parameters(board_id)
        validate_options(options, parameters.generalParameters)
        board = self.registry.get(board_id)
        board.set_global(options)
        return board.get_status()

    def set_group(self, board_id: str, group_id: str, options: dict[str, Any]) -> BoardStatus:
        parameters = self.get_board_parameters(board_id)
        validate_options(options, parameters.groupParameters)
        board = self.registry.get(board_id)
        board.set_group(group_id, options)
        return board.get_status()

    def set_channel(self, board_id: str, channel_id: str, options: dict[str, Any]) -> BoardStatus:
        parameters = self.get_board_parameters(board_id)
        validate_options(options, parameters.channelParameters)
        board = self.registry.get(board_id)
        board.set_channel(channel_id, options)
        return board.get_status()

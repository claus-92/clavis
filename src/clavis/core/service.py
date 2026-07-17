from typing import Any

from clavis.clients.registry import ClientRegistry
from clavis.core.errors import BoardConnectionError, ClavisError, InvalidBoardConfigurationError
from clavis.core.factory import BoardFactory
from clavis.core.registry import BoardRegistry
from clavis.parameters.validation import validate_options, validate_parameter_definitions
from clavis.plugins import BoardPluginRegistry, load_entry_point_plugins
from clavis.schemas import BoardConfig, BoardConfigEntry, BoardMetadata, BoardParameters, BoardStatus, BoardTypeInfo, ParameterDefinitions, SystemConfig


class ClavisService:
    def __init__(self) -> None:
        self.registry = BoardRegistry()
        self.board_configs: dict[str, BoardConfig] = {}
        self.plugins = BoardPluginRegistry()
        for plugin in load_entry_point_plugins():
            self.plugins.register(plugin)
        self.factory = BoardFactory(self.plugins, ClientRegistry())

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

    def get_system_config(self) -> SystemConfig:
        entries = []
        for board in self.registry.all():
            board_id = board.get_id()
            config = self.board_configs[board_id]
            status = board.get_status()
            params = BoardParameters(
                global_=status.global_options,
                groups=status.group_options,
                channels=status.channel_options,
            )
            entries.append(BoardConfigEntry(config=config, parameters=params))
        return SystemConfig(boards=entries)

    def apply_system_config(self, system_config: SystemConfig) -> SystemConfig:
        for board_id in [b.get_id() for b in self.registry.all()]:
            self.delete_board(board_id)
        for entry in system_config.boards:
            self.create_board(entry.config)
        for entry in system_config.boards:
            board_id = entry.config.board_id
            board = self.registry.get(board_id)
            board.connect()
            if entry.parameters.global_:
                self.set_global(board_id, entry.parameters.global_)
            for group_id, opts in entry.parameters.groups.items():
                self.set_group(board_id, group_id, opts)
            for channel_id, opts in entry.parameters.channels.items():
                self.set_channel(board_id, channel_id, opts)
        return self.get_system_config()

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
        parameters = plugin.load_parameters()
        validate_parameter_definitions(parameters)
        return parameters

    def connect_board(self, board_id: str) -> BoardStatus:
        board = self.registry.get(board_id)
        try:
            board.connect()
        except ClavisError:
            raise
        except Exception as exc:
            raise BoardConnectionError(f"Failed to connect board {board_id}: {exc}") from exc
        return board.get_status()

    def disconnect_board(self, board_id: str) -> BoardStatus:
        board = self.registry.get(board_id)
        try:
            board.disconnect()
        except ClavisError:
            raise
        except Exception as exc:
            raise BoardConnectionError(f"Failed to disconnect board {board_id}: {exc}") from exc
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

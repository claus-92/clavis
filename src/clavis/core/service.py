from typing import Any

from clavis.boards.fake import FakeAcquisitionBoard
from clavis.core.registry import BoardRegistry
from clavis.parameters.loader import load_parameter_definitions
from clavis.parameters.validation import validate_options
from clavis.schemas import BoardMetadata, BoardStatus, ParameterDefinitions
from clavis.transport.fake import FakeTransport


class ClavisService:
    def __init__(self) -> None:
        self.registry = BoardRegistry()
        self.parameters = load_parameter_definitions("samidare")
        self.discover_boards()

    def discover_boards(self) -> list[BoardMetadata]:
        for metadata in [
            BoardMetadata(board_id="dev-001", name="SAMIDARE Board_TPC_1", asic="SAMPA_v4", fpga="Artix_Ultrascale_Plus", firmware_version="FW_v_1_2_3"),
            BoardMetadata(board_id="dev-002", name="SAMIDARE Board_TPC_2", asic="SAMPA_v4", fpga="Artix_Ultrascale_Plus", firmware_version="FW_v_1_2_3"),
        ]:
            if metadata.board_id not in {board.get_id() for board in self.registry.all()}:
                self.registry.add(FakeAcquisitionBoard(metadata, FakeTransport()))
        return self.list_boards()

    def list_boards(self) -> list[BoardMetadata]:
        return [board.metadata for board in self.registry.all()]

    def get_board(self, board_id: str) -> BoardMetadata:
        return self.registry.get(board_id).metadata

    def get_board_status(self, board_id: str) -> BoardStatus:
        return self.registry.get(board_id).get_status()

    def get_board_parameters(self, board_id: str) -> ParameterDefinitions:
        self.registry.get(board_id)
        return self.parameters

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

    def set_global(self, board_id: str, options: dict[str, Any]) -> BoardStatus:
        validate_options(options, self.parameters.generalParameters)
        board = self.registry.get(board_id)
        board.set_global(options)
        return board.get_status()

    def set_group(self, board_id: str, group_id: str, options: dict[str, Any]) -> BoardStatus:
        validate_options(options, self.parameters.groupParameters)
        board = self.registry.get(board_id)
        board.set_group(group_id, options)
        return board.get_status()

    def set_channel(self, board_id: str, channel_id: str, options: dict[str, Any]) -> BoardStatus:
        validate_options(options, self.parameters.channelParameters)
        board = self.registry.get(board_id)
        board.set_channel(channel_id, options)
        return board.get_status()

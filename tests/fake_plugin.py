from typing import Any

from pydantic import BaseModel

from clavis.boards.base import AcquisitionBoard
from clavis.core.errors import BoardAlreadyAcquiringError, BoardAlreadyConnectedError, BoardNotAcquiringError, BoardNotConnectedError, BoardNotPoweredError
from clavis.plugins import BoardPlugin
from clavis.schemas import BoardMetadata, BoardStatus, ParameterDefinitions


class FakeBoardConfig(BaseModel):
    board_id: str
    board_type: str = "fake"
    name: str
    asic: str = "fake"
    fpga: str = "fake"
    firmware_version: str = "fake"


class FakeBoard(AcquisitionBoard):
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


def create_fake_board(config: BaseModel) -> FakeBoard:
    data = config.model_dump()
    fake_config = FakeBoardConfig(**data)
    metadata = BoardMetadata(
        board_id=fake_config.board_id,
        name=fake_config.name,
        asic=fake_config.asic,
        fpga=fake_config.fpga,
        firmware_version=fake_config.firmware_version,
        board_type="fake",
    )
    return FakeBoard(metadata)


def load_fake_parameters() -> ParameterDefinitions:
    return ParameterDefinitions(
        generalParameters=[{"name": "mode", "type": "string", "defaultValue": "normal", "options": ["normal", "calibration"], "description": "Test mode"}],
        channelParameters=[{"name": "power", "type": "string", "defaultValue": "off", "options": ["on", "off"], "description": "Test power"}, {"name": "gain", "type": "integer", "defaultValue": 1, "options": [1, 2, 4, 8], "description": "Test gain"}],
        groupParameters=[{"name": "threshold", "type": "integer", "defaultValue": 10, "options": [5, 10, 20], "description": "Test threshold"}],
    )


def plugin() -> BoardPlugin:
    return BoardPlugin(
        board_type="fake",
        display_name="Fake Board",
        config_model=FakeBoardConfig,
        create_board=create_fake_board,
        load_parameters=load_fake_parameters,
    )

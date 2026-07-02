from typing import Any

from clavis.boards.base import AcquisitionBoard
from clavis.core.errors import BoardAlreadyAcquiringError, BoardAlreadyConnectedError, BoardNotAcquiringError, BoardNotConnectedError, BoardNotPoweredError
from clavis.schemas import BoardMetadata, BoardStatus
from clavis.transport.base import Transport


class FakeAcquisitionBoard(AcquisitionBoard):
    def __init__(self, metadata: BoardMetadata, transport: Transport) -> None:
        self.metadata = metadata
        self.transport = transport
        self.connected = False
        self.powered = False
        self.acquiring = False
        self.global_options: dict[str, Any] = {}
        self.group_options: dict[str, dict[str, Any]] = {}
        self.channel_options: dict[str, dict[str, Any]] = {}

    def connect(self) -> None:
        if self.connected:
            raise BoardAlreadyConnectedError(f"Board already connected: {self.get_id()}")
        self.transport.open()
        self.connected = True

    def disconnect(self) -> None:
        if not self.connected:
            raise BoardNotConnectedError(f"Board not connected: {self.get_id()}")
        self.transport.close()
        self.connected = False
        self.powered = False
        self.acquiring = False

    def power_on(self) -> None:
        self._require_connected()
        self.powered = True

    def power_off(self) -> None:
        self._require_connected()
        self.acquiring = False
        self.powered = False

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

    def set_channel(self, channel_id: str, options: dict[str, Any]) -> None:
        self._require_connected()
        self.channel_options.setdefault(channel_id, {}).update(options)

    def set_group(self, group_id: str, options: dict[str, Any]) -> None:
        self._require_connected()
        self.group_options.setdefault(group_id, {}).update(options)

    def set_global(self, options: dict[str, Any]) -> None:
        self._require_connected()
        self.global_options.update(options)

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

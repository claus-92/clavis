from typing import Any

from clavis.boards.base import AcquisitionBoard
from clavis.schemas import BoardMetadata, BoardStatus


class ExampleBoard(AcquisitionBoard):
    def __init__(self, metadata: BoardMetadata) -> None:
        self.metadata = metadata

    def connect(self) -> None:
        raise NotImplementedError

    def disconnect(self) -> None:
        raise NotImplementedError

    def power_on(self) -> None:
        raise NotImplementedError

    def power_off(self) -> None:
        raise NotImplementedError

    def arm_acquisition(self) -> None:
        self._require_connected()
        self.acquiring = False

    def start_acquisition(self) -> None:
        raise NotImplementedError

    def stop_acquisition(self) -> None:
        raise NotImplementedError

    def set_channel(self, channel_id: str, options: dict[str, Any]) -> None:
        raise NotImplementedError

    def set_group(self, group_id: str, options: dict[str, Any]) -> None:
        raise NotImplementedError

    def set_global(self, options: dict[str, Any]) -> None:
        raise NotImplementedError

    def get_id(self) -> str:
        return self.metadata.board_id

    def get_status(self) -> BoardStatus:
        raise NotImplementedError

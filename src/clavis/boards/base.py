from abc import ABC, abstractmethod
from typing import Any

from clavis.schemas.board import BoardStatus
from clavis.transport.base import Transport


class AcquisitionBoard(ABC):
    def __init__(self, transport: Transport) -> None:
        self.transport = transport

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def power_on(self) -> None: ...

    @abstractmethod
    def power_off(self) -> None: ...

    @abstractmethod
    def set_channel(self, channel_id: str, options: dict[str, Any]) -> None: ...

    @abstractmethod
    def set_group(self, group_id: str, options: dict[str, Any]) -> None: ...

    @abstractmethod
    def set_global(self, options: dict[str, Any]) -> None: ...

    @abstractmethod
    def get_id(self) -> str: ...

    @abstractmethod
    def get_status(self) -> BoardStatus: ...

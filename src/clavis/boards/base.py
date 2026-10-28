from abc import ABC, abstractmethod
from typing import Any

from clavis.schemas import BoardStatus


class AcquisitionBoard(ABC):
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def power_on(self) -> None: ...

    @abstractmethod
    def power_off(self) -> None: ...

    @abstractmethod
    def arm_acquisition(self) -> None: ...

    @abstractmethod
    def start_acquisition(self) -> None: ...

    @abstractmethod
    def stop_acquisition(self) -> None: ...

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

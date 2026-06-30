from clavis.boards.base import AcquisitionBoard
from clavis.core.errors import BoardNotFoundError


class BoardRegistry:
    def __init__(self) -> None:
        self._boards: dict[str, AcquisitionBoard] = {}

    def add(self, board: AcquisitionBoard) -> None:
        self._boards[board.get_id()] = board

    def get(self, board_id: str) -> AcquisitionBoard:
        try:
            return self._boards[board_id]
        except KeyError as exc:
            raise BoardNotFoundError(f"Board not found: {board_id}") from exc

    def all(self) -> list[AcquisitionBoard]:
        return list(self._boards.values())

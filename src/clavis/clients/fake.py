from clavis.clients.base import RegisterClient


class FakeRegisterClient(RegisterClient):
    def __init__(self) -> None:
        self.is_open = False
        self.registers: dict[int, int] = {}

    def open(self) -> None:
        self.is_open = True

    def close(self) -> None:
        self.is_open = False

    def read_register(self, address: int) -> int:
        return self.registers.get(address, 0)

    def write_register(self, address: int, value: int) -> None:
        self.registers[address] = value

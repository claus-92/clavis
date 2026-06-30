from clavis.transport.base import Transport


class FakeTransport(Transport):
    def __init__(self) -> None:
        self.is_open = False
        self.last_sent = b""

    def open(self) -> None:
        self.is_open = True

    def close(self) -> None:
        self.is_open = False

    def send(self, data: bytes) -> None:
        self.last_sent = data

    def receive(self) -> bytes:
        return self.last_sent or b"ok"

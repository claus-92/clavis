import socket

from clavis.transport.base import Transport


class UdpTransport(Transport):
    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 0.1,
        max_packet_size: int = 2048,
        bind_host: str = "",
        bind_port: int = 0,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_packet_size = max_packet_size
        self.bind_host = bind_host
        self.bind_port = bind_port
        self._socket: socket.socket | None = None
        self._remote: tuple[str, int] | None = None

    def open(self) -> None:
        if self._socket is not None:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        sock.bind((self.bind_host, self.bind_port))
        self._remote = socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_DGRAM)[0][4]
        self._socket = sock

    def close(self) -> None:
        if self._socket is None:
            return
        self._socket.close()
        self._socket = None
        self._remote = None

    def send(self, data: bytes) -> None:
        sock = self._require_open()
        if self._remote is None:
            raise RuntimeError("UDP transport remote address is not resolved")
        sock.sendto(data, self._remote)

    def receive(self) -> bytes:
        sock = self._require_open()
        if self._remote is None:
            raise RuntimeError("UDP transport remote address is not resolved")
        while True:
            data, address = sock.recvfrom(self.max_packet_size)
            if address == self._remote:
                return data

    def _require_open(self) -> socket.socket:
        if self._socket is None:
            raise RuntimeError("UDP transport is not open")
        return self._socket

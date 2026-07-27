import socket

import pytest

from clavis.transport.udp import UdpTransport


def test_udp_transport_sends_and_receives_loopback_datagrams() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", 0))
    transport = UdpTransport("127.0.0.1", server.getsockname()[1], timeout=0.1)
    transport.open()
    try:
        transport.send(b"request")
        data, client_address = server.recvfrom(64)
        assert data == b"request"

        server.sendto(b"response", client_address)
        assert transport.receive() == b"response"
    finally:
        transport.close()
        server.close()


def test_udp_transport_filters_unexpected_sources() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", 0))
    unexpected = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    unexpected.bind(("127.0.0.1", 0))
    transport = UdpTransport("127.0.0.1", server.getsockname()[1], timeout=0.1)
    transport.open()
    try:
        transport.send(b"request")
        _, client_address = server.recvfrom(64)
        unexpected.sendto(b"wrong", client_address)
        server.sendto(b"right", client_address)

        assert transport.receive() == b"right"
    finally:
        transport.close()
        unexpected.close()
        server.close()


def test_udp_transport_times_out_and_requires_open_socket() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", 0))
    transport = UdpTransport("127.0.0.1", server.getsockname()[1], timeout=0.01)
    with pytest.raises(RuntimeError, match="not open"):
        transport.send(b"request")

    transport.open()
    try:
        with pytest.raises(TimeoutError):
            transport.receive()
    finally:
        transport.close()
        server.close()


def test_udp_transport_open_and_close_are_idempotent() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", 0))
    transport = UdpTransport("127.0.0.1", server.getsockname()[1])

    transport.open()
    transport.open()
    transport.close()
    transport.close()
    server.close()

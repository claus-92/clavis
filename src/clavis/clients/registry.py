from typing import Any

from clavis.clients.fakernet import FakernetRegisterClient
from clavis.clients.fake import FakeRegisterClient
from clavis.transport.fake import FakeTransport
from clavis.transport.udp import UdpTransport


class ClientRegistry:
    def create_transport(self, transport_type: str, **options: Any):
        if transport_type == "fake":
            return FakeTransport()
        if transport_type == "udp":
            return UdpTransport(**options)
        raise ValueError(f"Unknown transport type: {transport_type}")

    def create_client(self, client_type: str, **options: Any):
        if client_type == "fake":
            return FakeRegisterClient()
        if client_type == "fakernet":
            return FakernetRegisterClient(**options)
        raise ValueError(f"Unknown client type: {client_type}")

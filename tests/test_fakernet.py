from clavis.clients.fakernet import HEADER, SEQ_REQ_ARM_USER_CODE_MASK, SEQ_REQ_CONNECTED, SEQ_REQ_DISCONNECT, SEQ_REQ_RESET, SEQ_REQ_RESET_ARM, SEQ_SEQUENCE_MASK, SEQ_SEQUENCE_MASK_1ST_XOR, FakernetError, FakernetRegisterClient


class ReliableHandshakeTransport:
    def __init__(self, stale_once: bool = True) -> None:
        self.stale_once = stale_once
        self.is_open = False
        self.sent_sequences: list[int] = []
        self._last_sequence = 0

    def open(self) -> None:
        self.is_open = True

    def close(self) -> None:
        self.is_open = False

    def send(self, data: bytes) -> None:
        _, _, self._last_sequence, _ = HEADER.unpack(data)
        self.sent_sequences.append(self._last_sequence)

    def receive(self) -> bytes:
        if self._last_sequence & SEQ_REQ_RESET_ARM:
            key = self._last_sequence & SEQ_REQ_ARM_USER_CODE_MASK
            if self.stale_once:
                self.stale_once = False
                return HEADER.pack(0, 0, 0, key | SEQ_REQ_CONNECTED)
            return HEADER.pack(0, 0, 0, key | 0x05)
        if self._last_sequence & SEQ_REQ_DISCONNECT:
            return HEADER.pack(0, 0, 0, self._last_sequence)
        if self._last_sequence & SEQ_REQ_RESET:
            return HEADER.pack(0, 0, 0, self._last_sequence)
        raise AssertionError(f"Unexpected fakernet sequence: {self._last_sequence:#x}")


def test_reliable_open_disconnects_stale_channel_and_retries_handshake() -> None:
    transport = ReliableHandshakeTransport(stale_once=True)
    client = FakernetRegisterClient(transport, reliable=True)

    client.open()

    assert transport.sent_sequences[1] == SEQ_REQ_DISCONNECT
    assert transport.is_open is True
    assert client.is_open is True
    reset_sequence = transport.sent_sequences[-1]
    assert client.sequence_number == (((reset_sequence & SEQ_SEQUENCE_MASK) ^ SEQ_SEQUENCE_MASK_1ST_XOR) + 1) & SEQ_SEQUENCE_MASK


def test_reliable_open_closes_transport_when_stale_recovery_fails() -> None:
    transport = ReliableHandshakeTransport(stale_once=True)
    client = FakernetRegisterClient(transport, reliable=True, max_attempts=1)

    try:
        client.open()
    except FakernetError:
        pass
    else:
        raise AssertionError("Expected stale channel recovery failure")

    assert transport.is_open is False
    assert client.is_open is False

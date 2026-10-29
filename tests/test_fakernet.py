import struct
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from clavis.clients.fakernet import HEADER, ITEM, REG_ACCESS_ADDR_READ, REG_ACCESS_ADDR_READ_RET, REG_ACCESS_ADDR_WRITE, REG_ACCESS_ADDR_WRITTEN, REG_ACCESS_MAX_ITEMS, SEQ_REQ_ARM_USER_CODE_MASK, SEQ_REQ_CONNECTED, SEQ_REQ_DISCONNECT, SEQ_REQ_RESET, SEQ_REQ_RESET_ARM, SEQ_SEQUENCE_MASK, SEQ_SEQUENCE_MASK_1ST_XOR, FakernetError, FakernetRegisterClient, RegisterAccess
from clavis.transport.fake import FakeTransport


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


def make_response(request: bytes, *, sequence: int | None = None) -> bytes:
    _, _, request_sequence, _ = HEADER.unpack_from(request)
    response = bytearray(HEADER.pack(0, 0, 0, request_sequence if sequence is None else sequence))
    for offset in range(HEADER.size, len(request), ITEM.size):
        raw_address, data = ITEM.unpack_from(request, offset)
        flag = raw_address & 0xF0000000
        response_flag = REG_ACCESS_ADDR_WRITTEN if flag == REG_ACCESS_ADDR_WRITE else REG_ACCESS_ADDR_READ_RET
        response.extend(ITEM.pack(response_flag | (raw_address & 0x0FFFFFFF), data if flag == REG_ACCESS_ADDR_WRITE else 0x12345678))
    return bytes(response)


class ResponseTransport(FakeTransport):
    def __init__(self, failures: int = 0) -> None:
        super().__init__()
        self.failures = failures
        self.send_count = 0

    def send(self, data: bytes) -> None:
        self.send_count += 1
        super().send(data)

    def receive(self) -> bytes:
        if self.failures:
            self.failures -= 1
            raise TimeoutError
        return make_response(self.last_sent)


class QueuedResponseTransport(ResponseTransport):
    def __init__(self, failures: int = 0) -> None:
        super().__init__(failures=failures)
        self.responses: deque[bytes] = deque()

    def send(self, data: bytes) -> None:
        super().send(data)
        self.responses.append(make_response(data))

    def receive(self) -> bytes:
        if self.failures:
            self.failures -= 1
            raise TimeoutError
        if not self.responses:
            raise TimeoutError
        return self.responses.popleft()


def test_register_transaction_drains_duplicate_reply_after_timeout_retry() -> None:
    transport = QueuedResponseTransport(failures=1)
    client = FakernetRegisterClient(transport)

    # The retry leaves a second response queued, with a different packet length
    # and register addresses from the following transaction.
    client.transact([RegisterAccess(0x123, 0), RegisterAccess(0x124, 0)])
    client.write_register(0x456, 0xDEADBEEF)

    assert client.sequence_number == 2
    assert transport.send_count == 3
    assert not transport.responses


def test_register_transaction_bounds_stale_reply_drain() -> None:
    transport = QueuedResponseTransport()
    client = FakernetRegisterClient(transport, max_attempts=2)
    stale = make_response(client._encode_packet(9, [RegisterAccess(0x123, 0)]))
    transport.responses.extend([stale] * 10)

    with pytest.raises(FakernetError, match="expected sequence 0x0000, last received 0x0009"):
        client.read_register(0x123)

    assert transport.send_count == 1
    assert client.sequence_number == 0


def test_register_transaction_still_validates_matching_reply() -> None:
    transport = QueuedResponseTransport()
    client = FakernetRegisterClient(transport)
    transport.responses.append(make_response(client._encode_packet(0, [RegisterAccess(0x999, 0)])))

    with pytest.raises(FakernetError, match="address does not match"):
        client.read_register(0x123)

    assert client.sequence_number == 0


def test_concurrent_register_transactions_do_not_share_inflight_exchange() -> None:
    receiving = Event()
    release_response = Event()
    second_started = Event()
    second_sent = Event()

    class BlockingTransport(ResponseTransport):
        def send(self, data: bytes) -> None:
            super().send(data)
            if self.send_count > 1:
                second_sent.set()

        def receive(self) -> bytes:
            if self.send_count == 1:
                receiving.set()
                assert release_response.wait(2)
            return super().receive()

    transport = BlockingTransport()
    client = FakernetRegisterClient(transport)

    def second_read() -> int:
        second_started.set()
        return client.read_register(0x456)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(client.read_register, 0x123)
        try:
            assert receiving.wait(2)
            second = executor.submit(second_read)
            assert second_started.wait(2)
            assert not second_sent.wait(0.05)
        finally:
            release_response.set()
        assert first.result(timeout=2) == 0x12345678
        assert second.result(timeout=2) == 0x12345678

    assert client.sequence_number == 2
    assert transport.send_count == 2
    assert HEADER.unpack_from(transport.last_sent)[2] == 1


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


def test_register_transaction_encodes_and_decodes_reads_and_writes() -> None:
    transport = ResponseTransport()
    client = FakernetRegisterClient(transport)
    client.open()

    results = client.transact([RegisterAccess(0x123, 0, write=False), RegisterAccess(0x456, 0xDEADBEEF, write=True)])

    assert results[0].address == 0x123
    assert results[0].data == 0x12345678
    assert results[0].written is False
    assert results[1].address == 0x456
    assert results[1].data == 0xDEADBEEF
    assert results[1].written is True
    assert client.sequence_number == 1


def test_register_transaction_retries_timeouts() -> None:
    transport = ResponseTransport(failures=2)
    client = FakernetRegisterClient(transport, max_attempts=3)

    assert client.read_register(0x123) == 0x12345678
    assert transport.send_count == 3


def test_register_transaction_rejects_too_many_items() -> None:
    client = FakernetRegisterClient(FakeTransport())

    with pytest.raises(ValueError, match="at most"):
        client.transact([RegisterAccess(index, 0) for index in range(REG_ACCESS_MAX_ITEMS + 1)])


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda request, response: response[:-1], "length does not match"),
        (lambda request, response: HEADER.pack(0, 0, 1, 0) + response[HEADER.size :], "nonzero request sequence"),
        (lambda request, response: make_response(request, sequence=9), "wrong sequence"),
        (
            lambda request, response: response[: HEADER.size] + ITEM.pack(REG_ACCESS_ADDR_READ_RET | 0x124, 0),
            "address does not match",
        ),
        (
            lambda request, response: response[: HEADER.size] + ITEM.pack(REG_ACCESS_ADDR_WRITTEN | 0x123, 0),
            "read did not return data",
        ),
    ],
)
def test_register_response_validation(mutate, message: str) -> None:
    client = FakernetRegisterClient(FakeTransport())
    request = client._encode_packet(0, [RegisterAccess(0x123, 0)])
    response = make_response(request)

    with pytest.raises(FakernetError, match=message):
        client._decode_register_response(request, mutate(request, response))


def test_register_response_rejects_malformed_item_alignment() -> None:
    client = FakernetRegisterClient(FakeTransport())
    request = HEADER.pack(0, 0, 0, 0) + struct.pack("!I", REG_ACCESS_ADDR_READ | 0x123)

    with pytest.raises(FakernetError, match="Malformed"):
        client._decode_register_response(request, request)

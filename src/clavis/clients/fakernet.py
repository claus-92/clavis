import random
import struct
import time
from dataclasses import dataclass

from clavis.clients.base import RegisterClient
from clavis.transport.base import Transport


REG_ACCESS_ADDR_WRITE = 0x80000000
REG_ACCESS_ADDR_WRITTEN = 0x40000000
REG_ACCESS_ADDR_READ = 0x20000000
REG_ACCESS_ADDR_READ_RET = 0x10000000
REG_ACCESS_MAX_ITEMS = 116

SEQ_REQ_RESET_ARM = 0x8000
SEQ_REQ_RESET = 0x4000
SEQ_REQ_DISCONNECT = 0x2000
SEQ_REQ_CONNECTED = 0x1000
SEQ_REQ_ARM_USER_CODE_SHIFT = 8
SEQ_REQ_ARM_USER_CODE_MASK = 0x0F00
SEQ_SEQUENCE_MASK = 0x00FF
SEQ_SEQUENCE_MASK_1ST_XOR = 0x00F0

HEADER = struct.Struct("!HHHH")
ITEM = struct.Struct("!II")


@dataclass(frozen=True)
class RegisterAccess:
    address: int
    data: int
    write: bool = False


@dataclass(frozen=True)
class RegisterResult:
    address: int
    data: int
    written: bool = False


class FakernetError(RuntimeError):
    pass


class FakernetChannelAlreadyConnectedError(FakernetError):
    pass


class FakernetRegisterClient(RegisterClient):
    def __init__(self, transport: Transport, reliable: bool = False, max_attempts: int = 10) -> None:
        self.transport = transport
        self.reliable = reliable
        self.max_attempts = max_attempts
        self.sequence_number = 0
        self.is_open = False

    def open(self) -> None:
        self.transport.open()
        self.is_open = True
        try:
            if self.reliable:
                self._establish_connection()
        except Exception:
            self.transport.close()
            self.is_open = False
            raise

    def close(self) -> None:
        try:
            if self.is_open and self.reliable:
                self._terminate_connection()
        finally:
            self.transport.close()
            self.is_open = False

    def read_register(self, address: int) -> int:
        return self.transact([RegisterAccess(address=address, data=0, write=False)])[0].data

    def write_register(self, address: int, value: int) -> None:
        self.transact([RegisterAccess(address=address, data=value, write=True)])

    def transact(self, accesses: list[RegisterAccess]) -> list[RegisterResult]:
        if len(accesses) > REG_ACCESS_MAX_ITEMS:
            raise ValueError(f"Fakernet supports at most {REG_ACCESS_MAX_ITEMS} register items per packet")
        sequence = self.sequence_number & (SEQ_SEQUENCE_MASK | SEQ_REQ_ARM_USER_CODE_MASK)
        payload = self._encode_packet(sequence, accesses)
        response = self._send_receive(payload)
        results = self._decode_register_response(payload, response)
        self.sequence_number = (self.sequence_number + 1) & 0xFFFF
        return results

    def _send_receive(self, payload: bytes) -> bytes:
        last_error: Exception | None = None
        for _ in range(self.max_attempts):
            try:
                self.transport.send(payload)
                return self.transport.receive()
            except TimeoutError as exc:
                last_error = exc
            except OSError as exc:
                last_error = exc
        raise FakernetError("Fakernet request timed out") from last_error

    def _encode_packet(self, sequence_request: int, accesses: list[RegisterAccess]) -> bytes:
        data = bytearray(HEADER.pack(0, 0, sequence_request & 0xFFFF, 0))
        for access in accesses:
            flag = REG_ACCESS_ADDR_WRITE if access.write else REG_ACCESS_ADDR_READ
            data.extend(ITEM.pack(flag | (access.address & 0x0FFFFFFF), access.data & 0xFFFFFFFF))
        return bytes(data)

    def _decode_register_response(self, request: bytes, response: bytes) -> list[RegisterResult]:
        if len(request) != len(response):
            raise FakernetError("Fakernet response length does not match request length")
        if len(response) < HEADER.size or (len(response) - HEADER.size) % ITEM.size:
            raise FakernetError("Malformed fakernet response length")

        _, _, sequence_request, _ = HEADER.unpack(request[: HEADER.size])
        _, _, recv_sequence_request, sequence_response = HEADER.unpack(response[: HEADER.size])
        if recv_sequence_request != 0:
            raise FakernetError("Fakernet response has nonzero request sequence")
        if sequence_response != sequence_request:
            raise FakernetError("Fakernet response has wrong sequence number")

        results: list[RegisterResult] = []
        for offset in range(HEADER.size, len(response), ITEM.size):
            req_addr_raw, _ = ITEM.unpack(request[offset : offset + ITEM.size])
            res_addr_raw, res_data = ITEM.unpack(response[offset : offset + ITEM.size])
            req_addr = req_addr_raw & 0x0FFFFFFF
            res_addr = res_addr_raw & 0x0FFFFFFF
            req_flag = req_addr_raw & 0xF0000000
            res_flag = res_addr_raw & 0xF0000000
            if req_addr != res_addr:
                raise FakernetError("Fakernet response address does not match request")
            if req_flag == REG_ACCESS_ADDR_WRITE and res_flag != REG_ACCESS_ADDR_WRITTEN:
                raise FakernetError("Fakernet write was not acknowledged")
            if req_flag == REG_ACCESS_ADDR_READ and res_flag != REG_ACCESS_ADDR_READ_RET:
                raise FakernetError("Fakernet read did not return data")
            results.append(RegisterResult(address=res_addr, data=res_data, written=req_flag == REG_ACCESS_ADDR_WRITE))
        return results

    def _establish_connection(self) -> None:
        key = int(time.time()) ^ random.randint(0, 0xF)
        recovered_stale_channel = False
        for _ in range(self.max_attempts):
            key = (key + 1) & 0xF
            arm_sequence = SEQ_REQ_RESET_ARM | (key << SEQ_REQ_ARM_USER_CODE_SHIFT)
            arm_packet = HEADER.pack(0, 0, arm_sequence, 0)
            arm_response = self._send_receive(arm_packet)
            try:
                arm_no = self._check_reset_reply(arm_packet, arm_response) & SEQ_SEQUENCE_MASK
            except FakernetChannelAlreadyConnectedError:
                if recovered_stale_channel:
                    raise
                recovered_stale_channel = True
                self._terminate_connection()
                continue

            reset_sequence = SEQ_REQ_RESET | arm_no
            reset_packet = HEADER.pack(0, 0, reset_sequence, 0)
            reset_response = self._send_receive(reset_packet)
            sequence_response = self._check_reset_reply(reset_packet, reset_response)
            self.sequence_number = ((sequence_response & SEQ_SEQUENCE_MASK) ^ SEQ_SEQUENCE_MASK_1ST_XOR) + 1
            self.sequence_number &= SEQ_SEQUENCE_MASK
            return
        raise FakernetError("Failed to establish fakernet reliable channel")

    def _terminate_connection(self) -> None:
        packet = HEADER.pack(0, 0, SEQ_REQ_DISCONNECT, 0)
        self._send_receive(packet)

    def _check_reset_reply(self, request: bytes, response: bytes) -> int:
        if len(response) != HEADER.size:
            raise FakernetError("Malformed fakernet reset response length")
        _, _, request_sequence, _ = HEADER.unpack(request)
        _, _, recv_sequence_request, sequence_response = HEADER.unpack(response)
        if recv_sequence_request != 0:
            raise FakernetError("Fakernet reset response has nonzero request sequence")
        if (request_sequence & 0xE000) == SEQ_REQ_RESET_ARM:
            if (request_sequence & SEQ_REQ_ARM_USER_CODE_MASK) != (sequence_response & SEQ_REQ_ARM_USER_CODE_MASK):
                raise FakernetError("Fakernet arm response has wrong key")
            if sequence_response & SEQ_REQ_CONNECTED:
                raise FakernetChannelAlreadyConnectedError("Fakernet reliable channel is already connected")
            return sequence_response
        if (request_sequence & 0xE000) in {SEQ_REQ_RESET, SEQ_REQ_DISCONNECT}:
            if sequence_response != request_sequence:
                raise FakernetError("Fakernet reset/disconnect response has wrong sequence")
            return sequence_response
        raise FakernetError("Unexpected fakernet reset response")

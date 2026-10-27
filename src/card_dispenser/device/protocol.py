"""K720 serial frame encoding and decoding.

Pure functions only: no I/O, no timing. Source of truth is the vendor document
"Communication Protocol of K720&k730&k750" (see CLAUDE.md, section 7).
"""

from enum import IntFlag
from typing import Final

from card_dispenser.device.errors import DeviceNakError, DeviceProtocolError

STX: Final = 0x02
ETX: Final = 0x03
ENQ: Final = 0x05
ACK: Final = 0x06
NAK: Final = 0x15

MAX_ADDRESS: Final = 15
MAX_PAYLOAD_LEN: Final = 0xFFFF
# STX + ADDH + ADDL + LEN_H + LEN_L + ETX + BCC, i.e. a frame with an empty payload.
MIN_FRAME_LEN: Final = 7

CMD_STATUS: Final = b"AP"
CMD_DISPENSE: Final = b"DC"
CMD_RESET: Final = b"RS"

_STATUS_RESPONSE_PREFIX: Final = b"SF"
_STATUS_HEX_LEN: Final = 4


class DispenserState(IntFlag):
    """Bit field returned by the `AP` status command (4 ASCII hex digits)."""

    SENDING_CARD = 0x0800
    COLLECTING_CARD = 0x0400
    ISSUE_ERROR = 0x0200
    RECYCLE_ERROR = 0x0100
    HOPPER_FULL = 0x0080
    CARD_OVERLAP = 0x0040
    CARD_JAM = 0x0020
    CARD_PRE_EMPTY = 0x0010
    CARD_EMPTY = 0x0008
    CARD_AT_SENSOR_3 = 0x0004
    CARD_AT_SENSOR_2 = 0x0002
    CARD_AT_SENSOR_1 = 0x0001


DISPENSE_BLOCKING_STATES: Final = (
    DispenserState.ISSUE_ERROR
    | DispenserState.RECYCLE_ERROR
    | DispenserState.CARD_OVERLAP
    | DispenserState.CARD_JAM
    | DispenserState.CARD_EMPTY
)


def bcc(data: bytes) -> int:
    """Compute the XOR block check character over the given bytes.

    Args:
        data: Bytes from STX through ETX, inclusive.

    Returns:
        The XOR of all bytes, 0-255.
    """
    result = 0
    for byte in data:
        result ^= byte
    return result


def encode_address(address: int) -> bytes:
    """Encode a device address as the two ASCII digits ADDH ADDL.

    The address is set by the DIP switch on the device; the table in the vendor
    document maps e.g. address 5 to ASCII "05" (0x30 0x35).

    Args:
        address: Device address, 0-15.

    Returns:
        Two ASCII digit bytes.

    Raises:
        ValueError: If the address is outside 0-15.
    """
    if not 0 <= address <= MAX_ADDRESS:
        raise ValueError(f"device address must be 0-{MAX_ADDRESS}, got {address}")
    return f"{address:02d}".encode("ascii")


def build_frame(address: int, payload: bytes) -> bytes:
    """Build a command frame for the K720 protocol.

    Args:
        address: Device address, 0-15 (DIP switch setting).
        payload: Command bytes, e.g. b"AP" or b"\\x3B\\x31".

    Returns:
        The complete frame: STX, ADDH, ADDL, LEN_H, LEN_L, payload, ETX, BCC.

    Raises:
        ValueError: If the address is invalid or the payload is empty or too long.
    """
    if not payload or len(payload) > MAX_PAYLOAD_LEN:
        raise ValueError(f"payload must be 1-{MAX_PAYLOAD_LEN} bytes, got {len(payload)}")
    body = (
        bytes([STX])
        + encode_address(address)
        + len(payload).to_bytes(2, "big")
        + payload
        + bytes([ETX])
    )
    return body + bytes([bcc(body)])


def build_control_frame(control: int, address: int) -> bytes:
    """Build a three-byte control frame (ACK or ENQ) addressed to the device.

    Args:
        control: ENQ or ACK control byte.
        address: Device address, 0-15.

    Returns:
        control, ADDH, ADDL.
    """
    return bytes([control]) + encode_address(address)


def check_handshake(reply: bytes, address: int) -> None:
    """Validate the ACK reply to a command frame.

    Args:
        reply: The three bytes received after sending a command.
        address: Address the command was sent to.

    Raises:
        DeviceNakError: The device rejected the command format.
        DeviceProtocolError: The reply is not a valid ACK for this address.
    """
    if len(reply) != 3 or reply[1:] != encode_address(address):
        raise DeviceProtocolError(f"unexpected handshake reply: {reply.hex()}")
    if reply[0] == NAK:
        raise DeviceNakError(f"device rejected command at address {address}")
    if reply[0] != ACK:
        raise DeviceProtocolError(f"expected ACK, got 0x{reply[0]:02X}")


def parse_payload(frame: bytes, address: int) -> bytes:
    """Validate a response frame and return its payload.

    Args:
        frame: Complete response frame including STX and BCC.
        address: Address the response must come from.

    Returns:
        The payload bytes between the length field and ETX.

    Raises:
        DeviceProtocolError: Framing, length, address, ETX or BCC is wrong.
    """
    if len(frame) < MIN_FRAME_LEN or frame[0] != STX:
        raise DeviceProtocolError("response does not start with STX")
    if frame[1:3] != encode_address(address):
        raise DeviceProtocolError("response address does not match")
    length = int.from_bytes(frame[3:5], "big")
    if len(frame) != 5 + length + 2:
        raise DeviceProtocolError("response length field does not match frame size")
    if frame[-2] != ETX:
        raise DeviceProtocolError("response does not end with ETX")
    if bcc(frame[:-1]) != frame[-1]:
        raise DeviceProtocolError("response BCC mismatch")
    return frame[5 : 5 + length]


def parse_status_response(frame: bytes, address: int) -> DispenserState:
    """Decode the response to an `AP` status command.

    Args:
        frame: Complete response frame for the `AP` command.
        address: Address the response must come from.

    Returns:
        The decoded dispenser state flags. Unknown bits are kept.

    Raises:
        DeviceProtocolError: Frame is invalid or the status field is not hex.
    """
    payload = parse_payload(frame, address)
    if payload[:2] != _STATUS_RESPONSE_PREFIX or len(payload) != 2 + _STATUS_HEX_LEN:
        raise DeviceProtocolError("status response has unexpected payload")
    try:
        raw = int(payload[2:].decode("ascii"), 16)
    except ValueError as exc:
        raise DeviceProtocolError("status field is not hexadecimal") from exc
    return DispenserState(raw)

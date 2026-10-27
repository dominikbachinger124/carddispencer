import pytest

from card_dispenser.device.errors import DeviceNakError, DeviceProtocolError
from card_dispenser.device.protocol import (
    ACK,
    ENQ,
    ETX,
    NAK,
    STX,
    DispenserState,
    bcc,
    build_control_frame,
    build_frame,
    check_handshake,
    encode_address,
    parse_payload,
    parse_status_response,
)


def _response(address: int, payload: bytes) -> bytes:
    """Build a valid device response frame (test helper, mirrors the protocol)."""
    body = (
        bytes([STX])
        + encode_address(address)
        + len(payload).to_bytes(2, "big")
        + payload
        + bytes([ETX])
    )
    return body + bytes([bcc(body)])


def test_build_frame_ap_command_has_correct_bcc() -> None:
    frame = build_frame(address=0, payload=b"AP")

    assert frame[0] == STX
    assert frame[-2] == ETX
    assert frame[-1] == bcc(frame[:-1])


def test_build_frame_ap_command_has_expected_bytes() -> None:
    frame = build_frame(address=0, payload=b"AP")

    assert frame[:-1] == bytes([0x02, 0x30, 0x30, 0x00, 0x02, 0x41, 0x50, 0x03])


@pytest.mark.parametrize(
    ("address", "expected_ascii"),
    [(0, b"00"), (5, b"05"), (9, b"09"), (10, b"10"), (15, b"15")],
)
def test_encode_address_valid_returns_two_ascii_digits(address: int, expected_ascii: bytes) -> None:
    assert encode_address(address) == expected_ascii


@pytest.mark.parametrize("address", [-1, 16, 255])
def test_encode_address_out_of_range_raises_value_error(address: int) -> None:
    with pytest.raises(ValueError, match="device address"):
        encode_address(address)


def test_build_frame_empty_payload_raises_value_error() -> None:
    with pytest.raises(ValueError, match="payload"):
        build_frame(address=0, payload=b"")


def test_build_frame_length_field_is_big_endian() -> None:
    payload = b"x" * 0x0102
    frame = build_frame(address=0, payload=payload)

    assert frame[3:5] == b"\x01\x02"


def test_build_control_frame_enq_has_address_suffix() -> None:
    assert build_control_frame(ENQ, address=3) == bytes([0x05, 0x30, 0x33])


@pytest.mark.parametrize(
    ("data", "expected"),
    [(b"", 0x00), (b"\x01", 0x01), (b"\x01\x02", 0x03), (b"\xff\xff", 0x00)],
)
def test_bcc_xor_of_bytes_returns_expected(data: bytes, expected: int) -> None:
    assert bcc(data) == expected


def test_check_handshake_ack_same_address_passes() -> None:
    check_handshake(bytes([ACK]) + encode_address(0), address=0)


def test_check_handshake_nak_raises_nak_error() -> None:
    with pytest.raises(DeviceNakError):
        check_handshake(bytes([NAK]) + encode_address(0), address=0)


def test_check_handshake_wrong_address_raises_protocol_error() -> None:
    with pytest.raises(DeviceProtocolError):
        check_handshake(bytes([ACK]) + encode_address(1), address=0)


def test_check_handshake_short_reply_raises_protocol_error() -> None:
    with pytest.raises(DeviceProtocolError):
        check_handshake(bytes([ACK]), address=0)


def test_check_handshake_unknown_control_byte_raises_protocol_error() -> None:
    with pytest.raises(DeviceProtocolError):
        check_handshake(bytes([0x99]) + encode_address(0), address=0)


def test_parse_payload_valid_frame_returns_payload() -> None:
    frame = _response(0, b"SF0800")

    assert parse_payload(frame, address=0) == b"SF0800"


def test_parse_payload_bad_bcc_raises_protocol_error() -> None:
    frame = bytearray(_response(0, b"SF0800"))
    frame[-1] ^= 0xFF

    with pytest.raises(DeviceProtocolError, match="BCC"):
        parse_payload(bytes(frame), address=0)


def test_parse_payload_wrong_length_field_raises_protocol_error() -> None:
    frame = bytearray(_response(0, b"SF0800"))
    frame[4] += 1

    with pytest.raises(DeviceProtocolError, match="length"):
        parse_payload(bytes(frame), address=0)


def test_parse_payload_missing_stx_raises_protocol_error() -> None:
    frame = bytearray(_response(0, b"SF0800"))
    frame[0] = 0x00

    with pytest.raises(DeviceProtocolError, match="STX"):
        parse_payload(bytes(frame), address=0)


def test_parse_payload_wrong_address_raises_protocol_error() -> None:
    with pytest.raises(DeviceProtocolError, match="address"):
        parse_payload(_response(1, b"SF0800"), address=0)


def test_parse_payload_too_short_raises_protocol_error() -> None:
    with pytest.raises(DeviceProtocolError):
        parse_payload(b"\x02\x30\x30", address=0)


@pytest.mark.parametrize(
    ("hex_status", "expected"),
    [
        (b"0800", DispenserState.SENDING_CARD),
        (b"0008", DispenserState.CARD_EMPTY),
        (b"0010", DispenserState.CARD_PRE_EMPTY),
        (b"0020", DispenserState.CARD_JAM),
        (b"0040", DispenserState.CARD_OVERLAP),
        (b"0002", DispenserState.CARD_AT_SENSOR_2),
        (b"0000", DispenserState(0)),
    ],
)
def test_parse_status_response_known_bits_returns_flags(
    hex_status: bytes, expected: DispenserState
) -> None:
    frame = _response(0, b"SF" + hex_status)

    assert parse_status_response(frame, address=0) == expected


def test_parse_status_response_combined_bits_returns_all_flags() -> None:
    frame = _response(0, b"SF0028")

    state = parse_status_response(frame, address=0)

    assert DispenserState.CARD_JAM in state
    assert DispenserState.CARD_EMPTY in state


def test_parse_status_response_non_hex_field_raises_protocol_error() -> None:
    frame = _response(0, b"SFZZZZ")

    with pytest.raises(DeviceProtocolError, match="hexadecimal"):
        parse_status_response(frame, address=0)


def test_parse_status_response_wrong_prefix_raises_protocol_error() -> None:
    frame = _response(0, b"XX0008")

    with pytest.raises(DeviceProtocolError, match="unexpected payload"):
        parse_status_response(frame, address=0)


def test_parse_payload_missing_etx_raises_protocol_error() -> None:
    body = bytes([STX]) + encode_address(0) + (2).to_bytes(2, "big") + b"SF"
    frame = body + b"\x00" + bytes([bcc(body + b"\x00")])

    with pytest.raises(DeviceProtocolError, match="ETX"):
        parse_payload(frame, address=0)

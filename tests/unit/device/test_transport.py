from unittest.mock import MagicMock

import pytest
import serial

from card_dispenser.device import transport as transport_module
from card_dispenser.device.errors import DeviceTimeoutError
from card_dispenser.device.transport import FakeTransport, SerialTransport


def test_fake_transport_write_records_bytes() -> None:
    fake = FakeTransport()

    fake.write(b"\x02\x03")
    fake.write(b"\x04")

    assert fake.written == [b"\x02\x03", b"\x04"]


def test_fake_transport_read_returns_queued_reply() -> None:
    fake = FakeTransport([b"\x06\x30\x30"])

    assert fake.read(3) == b"\x06\x30\x30"


def test_fake_transport_queue_reply_appends_in_order() -> None:
    fake = FakeTransport()
    fake.queue_reply(b"A")
    fake.queue_reply(b"B")

    assert fake.read(1) == b"A"
    assert fake.read(1) == b"B"


def test_fake_transport_read_without_reply_raises_timeout() -> None:
    with pytest.raises(DeviceTimeoutError, match="no scripted reply"):
        FakeTransport().read(1)


def test_fake_transport_read_wrong_size_raises_timeout() -> None:
    fake = FakeTransport([b"\x06"])

    with pytest.raises(DeviceTimeoutError, match="expected"):
        fake.read(3)


def test_fake_transport_close_is_noop() -> None:
    FakeTransport().close()


def test_serial_transport_opens_port_with_k720_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    port_mock = MagicMock()
    monkeypatch.setattr(transport_module.serial, "Serial", MagicMock(return_value=port_mock))

    SerialTransport("/dev/ttyUSB0", timeout_s=0.5)

    transport_module.serial.Serial.assert_called_once_with(
        port="/dev/ttyUSB0",
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=0.5,
    )


def test_serial_transport_write_sends_and_flushes(monkeypatch: pytest.MonkeyPatch) -> None:
    port_mock = MagicMock()
    monkeypatch.setattr(transport_module.serial, "Serial", MagicMock(return_value=port_mock))
    transport = SerialTransport("COM3")

    transport.write(b"\x02")

    port_mock.write.assert_called_once_with(b"\x02")
    port_mock.flush.assert_called_once()


def test_serial_transport_read_full_reply_returns_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    port_mock = MagicMock()
    port_mock.read.return_value = b"\x06\x30\x30"
    monkeypatch.setattr(transport_module.serial, "Serial", MagicMock(return_value=port_mock))
    transport = SerialTransport("COM3")

    assert transport.read(3) == b"\x06\x30\x30"


def test_serial_transport_read_short_reply_raises_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    port_mock = MagicMock()
    port_mock.read.return_value = b"\x06"
    monkeypatch.setattr(transport_module.serial, "Serial", MagicMock(return_value=port_mock))
    transport = SerialTransport("COM3")

    with pytest.raises(DeviceTimeoutError, match="COM3"):
        transport.read(3)


def test_serial_transport_close_closes_port(monkeypatch: pytest.MonkeyPatch) -> None:
    port_mock = MagicMock()
    monkeypatch.setattr(transport_module.serial, "Serial", MagicMock(return_value=port_mock))
    transport = SerialTransport("COM3")

    transport.close()

    port_mock.close.assert_called_once()

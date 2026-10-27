"""Byte transports for the K720: real serial port and an in-memory fake for tests."""

from collections import deque
from typing import Final, Protocol

import serial
import structlog

from card_dispenser.device.errors import DeviceTimeoutError

log = structlog.get_logger(__name__)

BAUD_RATE: Final = 9600


class Transport(Protocol):
    """Half-duplex byte channel to the dispenser."""

    def write(self, data: bytes) -> None:
        """Send bytes to the device.

        Args:
            data: Bytes to transmit.
        """
        ...

    def read(self, size: int) -> bytes:
        """Read exactly ``size`` bytes from the device.

        Args:
            size: Number of bytes to read.

        Returns:
            The bytes read.

        Raises:
            DeviceTimeoutError: Fewer than ``size`` bytes arrived in time.
        """
        ...

    def close(self) -> None:
        """Release the underlying channel."""
        ...


class SerialTransport:
    """Transport backed by pyserial (``/dev/ttyUSB0`` on Linux, ``COM3`` on Windows).

    Attributes:
        port: Serial port name as configured by the user.
    """

    def __init__(self, port: str, timeout_s: float = 1.0) -> None:
        """Open the serial port with the K720 settings (9600 8N1).

        Args:
            port: Serial port name.
            timeout_s: Per-read timeout in seconds.
        """
        self.port = port
        self._serial = serial.Serial(
            port=port,
            baudrate=BAUD_RATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout_s,
        )
        log.info("serial_port_opened", port=port, baud=BAUD_RATE)

    def write(self, data: bytes) -> None:
        """Send bytes to the device.

        Args:
            data: Bytes to transmit.
        """
        self._serial.write(data)
        self._serial.flush()

    def read(self, size: int) -> bytes:
        """Read exactly ``size`` bytes from the device.

        Args:
            size: Number of bytes to read.

        Returns:
            The bytes read.

        Raises:
            DeviceTimeoutError: Fewer than ``size`` bytes arrived before the timeout.
        """
        data: bytes = self._serial.read(size)
        if len(data) != size:
            raise DeviceTimeoutError(f"expected {size} bytes on {self.port}, got {len(data)}")
        return data

    def close(self) -> None:
        """Close the serial port."""
        self._serial.close()
        log.info("serial_port_closed", port=self.port)


class FakeTransport:
    """In-memory transport for tests: records writes and replays scripted replies.

    Attributes:
        written: Every chunk passed to ``write``, in order.
    """

    def __init__(self, replies: list[bytes] | None = None) -> None:
        """Create a fake transport.

        Args:
            replies: Byte chunks returned by successive ``read`` calls.
        """
        self.written: list[bytes] = []
        self._replies: deque[bytes] = deque(replies or [])

    def queue_reply(self, data: bytes) -> None:
        """Append a reply that a later ``read`` will consume.

        Args:
            data: Bytes returned by the next read.
        """
        self._replies.append(data)

    def write(self, data: bytes) -> None:
        """Record bytes written to the device.

        Args:
            data: Bytes sent by the host.
        """
        self.written.append(data)

    def read(self, size: int) -> bytes:
        """Return the next scripted reply.

        Args:
            size: Expected reply size.

        Returns:
            The scripted bytes.

        Raises:
            DeviceTimeoutError: No reply is queued, or the queued reply has the wrong size.
        """
        if not self._replies:
            raise DeviceTimeoutError("no scripted reply left")
        data = self._replies.popleft()
        if len(data) != size:
            raise DeviceTimeoutError(f"scripted reply has {len(data)} bytes, expected {size}")
        return data

    def close(self) -> None:
        """No-op for the fake transport."""

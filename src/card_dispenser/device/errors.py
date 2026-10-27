"""Typed errors raised by the K720 device layer."""


class DeviceError(Exception):
    """Base class for all K720 communication errors."""


class DeviceTimeoutError(DeviceError):
    """Device did not answer within the protocol timeout."""


class DeviceNakError(DeviceError):
    """Device replied NAK (0x15): frame format error."""


class DeviceProtocolError(DeviceError):
    """Device reply is malformed: bad framing, BCC, length, address or payload."""

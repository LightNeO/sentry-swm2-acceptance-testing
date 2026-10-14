"""Moves bytes to/from the DUT. Driver never touches pyserial directly - same logic works
against a real UART (SerialTransport) or the scripted fake (FakeTransport).
"""

from __future__ import annotations

import os
import time
from typing import Protocol

import serial
from serial.tools import list_ports

BAUD = 115200


class Transport(Protocol):
    def write(self, data: bytes) -> None: ...
    def read(self, timeout: float) -> bytes: ...
    def flush_input(self) -> None: ...
    def reset_device(self) -> None: ...
    def close(self) -> None: ...


def find_port(vid: int | None = None, serial_number: str | None = None) -> str:
    """Find exactly one DUT port by USB VID (+ optional serial number) - never by COM number/position."""
    vid = vid if vid is not None else int(os.environ.get("SWM_VID", "0403"), 16)
    serial_number = serial_number or os.environ.get("SWM_SERIAL") or None
    ports = [p for p in list_ports.comports() if p.vid == vid]
    if serial_number:
        ports = [p for p in ports if serial_number.casefold() in (p.serial_number or "").casefold()]
    if len(ports) == 1:
        return ports[0].device
    found = "; ".join(f"{p.device} vid={p.vid} sn={p.serial_number}" for p in list_ports.comports()) or "<none>"
    raise RuntimeError(
        f"Expected exactly 1 DUT port for VID {vid:#06x}, got {len(ports)}. Set SWM_PORT or SWM_SERIAL. Ports: {found}"
    )


class SerialTransport:
    """Real UART 115200 8N1."""

    def __init__(self, port: str) -> None:
        self.port = port
        self.ser = serial.Serial(
            port, BAUD, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0.05
        )
        self.ser.reset_input_buffer()

    def write(self, data: bytes) -> None:
        self.ser.write(data)
        self.ser.flush()

    def read(self, timeout: float) -> bytes:
        """Block up to ``timeout`` for at least one byte, then grab whatever else is waiting."""
        self.ser.timeout = timeout
        first = self.ser.read(1)
        if not first:
            return b""
        return first + self.ser.read(self.ser.in_waiting)

    def flush_input(self) -> None:
        self.ser.reset_input_buffer()

    def reset_device(self) -> None:
        """Reset via FTDI RTS line (wired to EN). DTR stays low so GPIO0 doesn't get pulled."""
        self.ser.dtr = False
        self.ser.rts = True
        time.sleep(0.1)
        self.ser.rts = False
        time.sleep(0.05)

    def close(self) -> None:
        if self.ser.is_open:
            self.ser.close()


class FakeTransport:
    """Scripted fake DUT for testing the driver without hardware.

    ``script`` maps a command line to the reply text. Echoes the command first like the real DUT.
    A reply can skip the trailing newline to fake a prompt (``Password: ``).
    """

    def __init__(self, script: dict[str, str | list[str]] | None = None, boot_text: str = "") -> None:
        self.script = script or {}
        self.boot_text = boot_text
        self.sent: list[str] = []
        self._queue = bytearray()
        self.closed = False

    def write(self, data: bytes) -> None:
        for cmd in data.decode().replace("\r", "").split("\n"):
            if not cmd:
                continue
            self.sent.append(cmd)
            reply = self.script.get(cmd, f"E (1) sentry: E001 unknown command '{cmd}'. Type 'help'\n")
            if isinstance(reply, list):  # same command gives successive replies, last one repeats
                reply = reply.pop(0) if len(reply) > 1 else reply[0]
            self._queue += f"{cmd}\n{reply}".encode()

    def read(self, timeout: float) -> bytes:
        if not self._queue:
            time.sleep(min(timeout, 0.002))
            return b""
        data, self._queue = bytes(self._queue), bytearray()
        return data

    def flush_input(self) -> None:
        self._queue.clear()

    def reset_device(self) -> None:
        self._queue = bytearray(self.boot_text.encode())

    def close(self) -> None:
        self.closed = True

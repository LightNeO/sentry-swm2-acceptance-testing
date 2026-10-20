"""Serial driver for the Arduino Nano K1-K4 hardware stimulator."""

from __future__ import annotations

import os
import time

import serial


class ButtonStimulator:
    """Drive physical button inputs through an Arduino-controlled isolator board."""

    def __init__(self, port: str | None = None, baud: int = 115200, timeout: float = 2.0) -> None:
        self.port = port or os.environ.get("BUTTON_STIM_PORT")
        if not self.port:
            raise ValueError("BUTTON_STIM_PORT is not set")
        self.serial = serial.Serial(self.port, baudrate=baud, timeout=timeout)
        time.sleep(2.0)  # Nano resets when its USB serial port opens.
        self.serial.reset_input_buffer()
        self._command("PING", "PONG")

    def _command(self, command: str, expected: str | None = None) -> str:
        self.serial.write((command + "\n").encode("ascii"))
        self.serial.flush()
        reply = self.serial.readline().decode("ascii", errors="replace").strip()
        if expected and reply != expected:
            raise RuntimeError(f"stimulator: expected {expected!r}, got {reply!r}")
        if reply.startswith("ERR"):
            raise RuntimeError(f"stimulator rejected {command!r}: {reply}")
        return reply

    def press(self, button: str, duration_ms: int = 150) -> None:
        self.hold(button, duration_ms)

    def hold(self, button: str, duration_ms: int) -> None:
        self._validate_button(button)
        self._run(f"HOLD {button.upper()} {duration_ms}", button.upper(), duration_ms)

    def combo(self, buttons: tuple[str, ...], duration_ms: int = 2000) -> None:
        if not buttons:
            raise ValueError("combo needs at least one button")
        names = tuple(button.upper() for button in buttons)
        for button in names:
            self._validate_button(button)
        self._run(f"HOLD {'+'.join(names)} {duration_ms}", "+".join(names), duration_ms)

    def _run(self, command: str, buttons: str, duration_ms: int) -> None:
        if not 1 <= duration_ms <= 10000:
            raise ValueError("duration_ms must be between 1 and 10000")
        # The Arduino sends its acknowledgement after the hold has finished.
        # A fixed 2 s serial timeout races with the 2 s combo boundary.
        previous_timeout = self.serial.timeout
        self.serial.timeout = max(previous_timeout or 0.0, duration_ms / 1000 + 1.0)
        try:
            reply = self._command(command)
        finally:
            self.serial.timeout = previous_timeout
        expected = f"OK {buttons} {duration_ms}"
        if reply != expected:
            raise RuntimeError(f"stimulator: expected {expected!r}, got {reply!r}")

    @staticmethod
    def _validate_button(button: str) -> None:
        if button.upper() not in {"K1", "K2", "K3", "K4"}:
            raise ValueError(f"unknown button {button!r}")

    def close(self) -> None:
        if self.serial.is_open:
            try:
                self._command("STOP")
            finally:
                self.serial.close()

    def __enter__(self) -> ButtonStimulator:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

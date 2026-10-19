"""Small parsers shared by tests. They read the DUT's own output (formats captured from hardware in logs/)."""

from __future__ import annotations

import re
import time

from drivers.protocol import Response


def status_field(dut, name: str) -> str:
    """Value of a ``status`` line, e.g. status_field(dut, 'state') -> '1 NORMAL'; 'user' -> 'qa_swm (user)'."""
    m = dut.exchange("status", idle=0.8).search(rf"{name}:\s+(.+)")
    assert m, f"'status' has no '{name}:' line"
    return m.group(1).strip()


def current_state(dut) -> str:
    """Name of the current system state: 'NORMAL', 'DEBUG', 'VERBOSE' or 'EMERGENCY'."""
    return status_field(dut, "state").split()[-1]


def uptime_seconds(dut) -> int:
    m = re.search(r"uptime (\d+)h (\d+)m (\d+)s", status_field(dut, "time"))
    assert m, "cannot parse uptime from 'status'"
    h, mi, s = map(int, m.groups())
    return h * 3600 + mi * 60 + s


def relay_cycles(dut) -> int:
    """The ``cycles N`` counter from ``relay status``."""
    m = dut.exchange("relay status").search(r"cycles (\d+)")
    assert m, "'relay status' has no cycles counter"
    return int(m.group(1))


def telemetry_intervals_ms(resp: Response) -> list[int]:
    """Gaps between consecutive '[TELEMETRY #N]' reports, from the DUT's own millisecond ticks."""
    ticks = [l.tick for l in resp.lines if l.msg.startswith("[TELEMETRY #") and l.tick is not None]
    return [b - a for a, b in zip(ticks, ticks[1:])]


def lockout_seconds(resp: Response) -> int | None:
    """Remaining lockout from 'Try again in N s', if present."""
    m = resp.search(r"Try again in (\d+) s")
    return int(m.group(1)) if m else None


def reconnect_with_retries(dut, attempts: int = 3, pause: float = 2.0):
    """'reconnect' that survives the known first-attempt E101 (OBS-01): retry on E101 only, log every retry in the
    transcript, and return the last reply. Anything else (or E101 on every attempt) is returned as it is, so the
    caller's assert still fails when the link really does not come back."""
    reply = None
    for attempt in range(1, attempts + 1):
        reply = dut.exchange("reconnect", until=r"connected to|W114|E1\d\d", timeout=30)
        if not reply.has_code("E101"):
            break
        dut.transcript.add("TX", f"<retry {attempt}/{attempts}: reconnect returned E101>")
        time.sleep(pause)
    return reply


def wait_internet(dut, timeout: float = 40.0) -> bool:
    """Poll ``status`` until the DUT itself reports 'internet: OK' (its own check lags a few seconds behind the link)."""
    deadline = time.monotonic() + timeout
    while True:
        m = dut.exchange("status", idle=0.8).search(r"internet:\s+(\w+)")
        if m and m.group(1).upper() == "OK":
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(3)


def wait_link(dut, timeout: float = 45.0) -> bool:
    """Wait until the DUT has its Wi-Fi link, nudging it with 'reconnect' (the first attempt may give E101, OBS-01)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if dut.link_up():
            return True
        dut.exchange("reconnect", until=r"connected to|W114|E1\d\d", timeout=20)
        time.sleep(2)
    return dut.link_up()

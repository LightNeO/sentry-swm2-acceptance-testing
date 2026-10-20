"""Small parsers shared by tests. They read the DUT's own output (formats captured from hardware in logs/)."""

from __future__ import annotations

import re

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
    ticks = [line.tick for line in resp.lines if line.msg.startswith("[TELEMETRY #") and line.tick is not None]
    return [b - a for a, b in zip(ticks, ticks[1:], strict=False)]


def lockout_seconds(resp: Response) -> int | None:
    """Remaining lockout from 'Try again in N s', if present."""
    m = resp.search(r"Try again in (\d+) s")
    return int(m.group(1)) if m else None

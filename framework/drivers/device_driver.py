"""SWM-2 driver: wraps a Transport (raw bytes) in the console's command/response protocol.
No pytest stuff in here, just commands/prompts/flows.
"""

from __future__ import annotations

import re
import time

from drivers.components import Alerts, Guard, Lamp, Ota, Relay, Sonar, Wifi
from drivers.protocol import BOOT_READY_RE, VERSION_RE, Response, clean_text
from drivers.redaction import Redactor
from drivers.transport import Transport
from drivers.waiting import wait_until

CRLF = "\r\n"

# Boot says "known network 'X'" when a network is saved and "no known network" when it is not;
# the second also contains the first as a substring, so exclude it explicitly.
_SAVED_NETWORK_RE = re.compile(r"(?<!no )known network")


def has_saved_network(boot_text: str) -> bool:
    return bool(_SAVED_NETWORK_RE.search(boot_text))


class Transcript:
    """Log of everything sent to/received from the DUT - this is the test evidence."""

    def __init__(self) -> None:
        self._t0 = time.monotonic()
        self.entries: list[tuple[float, str, str]] = []

    def add(self, direction: str, text: str) -> None:
        self.entries.append((time.monotonic() - self._t0, direction, text))

    def clear(self) -> None:
        self._t0 = time.monotonic()
        self.entries.clear()

    def render(self) -> str:
        out = []
        for t, direction, text in self.entries:
            body = text.rstrip("\n")
            out.append(f"[{t:8.2f}s] {direction}: {body}" if direction == "TX" else f"[{t:8.2f}s] {direction}:\n{body}")
        return "\n".join(out) + "\n"


class SwmDevice:
    """High-level wrapper around one SWM-2 console."""

    SETTLE = 0.15  # seconds of silence that end a reply after its end marker was seen

    def __init__(
        self,
        transport: Transport,
        redactor: Redactor | None = None,
        timeout: float = 3.0,
        idle: float = 0.7,
    ) -> None:
        self.transport = transport
        self.redactor = redactor or Redactor()
        self.timeout = timeout
        self.idle = idle
        self.transcript = Transcript()
        self.boot_text = ""  # boot log of the session (set by the session fixture)
        self.fw_version = "unknown"  # e.g. "2.3.0"
        self.lamp = Lamp(self)
        self.relay = Relay(self)
        self.guard = Guard(self)
        self.alerts = Alerts(self)
        self.sonar = Sonar(self)
        self.ota = Ota(self)
        self.wifi = Wifi(self)

    # ------------------------------------------------------------------ low level
    def _collect(self, timeout: float, idle: float, until: str | None) -> tuple[str, bool]:
        """Read until ``until`` matches, or if no ``until``, until the line goes quiet.

        Returns (text, timed_out). Checks the whole buffer incl. a trailing partial line since
        prompts like ``Password: `` have no newline.
        """
        pattern = re.compile(until) if until else None
        deadline = time.monotonic() + timeout
        text, last_rx = "", None
        while True:
            now = time.monotonic()
            if now >= deadline:
                return text, (pattern is not None) or last_rx is None
            chunk = self.transport.read(min(0.05, deadline - now))
            if chunk:
                text += clean_text(chunk)
                last_rx = time.monotonic()
                if pattern and pattern.search(text):
                    # marker can land mid-line (UART bursts bytes) - drain until quiet or the tail leaks into next reply
                    while True:
                        more = self.transport.read(self.SETTLE)
                        if not more:
                            return text, False
                        text += clean_text(more)
            elif pattern is None and last_rx is not None and time.monotonic() - last_rx >= idle:
                return text, False

    def exchange(
        self,
        command: str,
        *,
        timeout: float | None = None,
        idle: float | None = None,
        until: str | None = None,
        secret: bool = False,
    ) -> Response:
        """Send one command line, capture the reply.

        until   regex marking end of reply (slow commands / prompts); default just waits for ``idle`` silence.
        secret  mask sent text in transcript (passwords).
        """
        self.transport.flush_input()
        self.transcript.add("TX", "***" if secret else self.redactor.clean(command))
        started = time.monotonic()
        self.transport.write((command + CRLF).encode("utf-8"))
        text, timed_out = self._collect(self.timeout if timeout is None else timeout, self.idle if idle is None else idle, until)
        text = self.redactor.clean(text)
        # DUT echoes the command back - strip it so tests only see the reply
        first, _, rest = text.partition("\n")
        if first.strip() == command.strip() and not secret:
            text = rest
        self.transcript.add("RX", text)
        return Response.from_text(command, text, timed_out, time.monotonic() - started)

    def read_for(self, seconds: float) -> Response:
        """Just listen for a fixed time (e.g. to measure telemetry interval)."""
        started = time.monotonic()
        text = ""
        while time.monotonic() - started < seconds:
            chunk = self.transport.read(min(0.2, seconds - (time.monotonic() - started)))
            if chunk:
                text += clean_text(chunk)
        text = self.redactor.clean(text)
        self.transcript.add("RX", text)
        return Response.from_text("<passive>", text, False, time.monotonic() - started)

    def wait_for(self, pattern: str, timeout: float) -> Response:
        """Wait for a text marker; raises TimeoutError (with captured text) so a hang fails loudly."""
        text, timed_out = self._collect(timeout, self.idle, pattern)
        text = self.redactor.clean(text)
        self.transcript.add("RX", text)
        if timed_out:
            raise TimeoutError(f"Marker {pattern!r} not seen within {timeout}s. Captured:\n{text}")
        return Response.from_text(f"<wait {pattern}>", text)

    # ------------------------------------------------------------------ device lifecycle
    def hard_reset(self, timeout: float = 20.0) -> Response:
        """Reset via RTS, return the boot log up to ``ready. state 1 NORMAL``."""
        self.transcript.add("TX", "<hardware reset via RTS>")
        self.transport.flush_input()
        self.transport.reset_device()
        boot = self.wait_for(BOOT_READY_RE.pattern, timeout)
        tail, _ = self._collect(0.5, 0.3, None)
        return Response.from_text("<boot>", boot.text + self.redactor.clean(tail))

    def reboot(self, timeout: float = 20.0) -> Response:
        """``reboot`` command (3-2-1 countdown), returns the boot log."""
        self.transcript.add("TX", "reboot")
        self.transport.flush_input()
        self.transport.write(("reboot" + CRLF).encode())
        boot = self.wait_for(BOOT_READY_RE.pattern, timeout)
        tail, _ = self._collect(0.5, 0.3, None)
        return Response.from_text("<boot>", boot.text + self.redactor.clean(tail))

    def version(self) -> str:
        """Firmware version from ``version``, e.g. ``2.1.0``."""
        m = VERSION_RE.search(self.exchange("version").text)
        if not m:
            raise RuntimeError("Cannot read firmware version from 'version' output")
        return m.group(1)

    # ------------------------------------------------------------------ Wi-Fi and account flows
    def connect_wifi(self, ssid: str, password: str) -> Response:
        """Interactive ``connect`` dialog: SSID prompt, password prompt, wait for 'network saved'."""
        self.redactor.add(password)
        parts = [self.exchange("connect", until=r"SSID or number:", timeout=10)]
        parts.append(self.exchange(ssid, until=r"Password:|E1\d\d", timeout=5))
        parts.append(self.exchange(password, secret=True, until=r"network saved|E1\d\d", timeout=45))
        return Response.from_text("connect", "\n".join(p.text for p in parts), any(p.timed_out for p in parts))

    def ensure_wifi(self, boot_text: str, ssid: str, password: str, attempts: int = 3, settle: float = 8.0) -> Response:
        """Bring Wi-Fi up after boot: ``reconnect`` if DUT remembers a network, else ``connect``.

        OBS-01 (bugs/Improvements.md): after a hard reset, first ``reconnect`` often returns E101 even with
        the right password, retry succeeds. Only retry on E101, and log the retry so it's visible in evidence.
        """
        if not has_saved_network(boot_text):
            return self.connect_wifi(ssid, password)
        r = self.exchange("reconnect", until=r"connected to|E1\d\d", timeout=30)
        for attempt in range(2, attempts + 1):
            if not r.has_code("E101"):
                break
            self.transcript.add("TX", f"<retry {attempt}/{attempts}: reconnect returned E101>")
            r = self.exchange("reconnect", until=r"connected to|E1\d\d", timeout=30)
        # NTP/internet checks land a few seconds after 'connected' - don't race them
        self._collect(settle, 1.5, r"time: synced|W106|E105")
        return r

    def link_up(self) -> bool:
        """True if ``status`` shows the Wi-Fi link up (works without login)."""
        r = self.exchange("status", idle=0.6)
        m = r.search(r"link:\s*(.+)")
        return bool(m) and "down" not in m.group(1).lower()

    def reconnect_with_retries(self, attempts: int = 3, pause: float = 2.0) -> Response:
        """'reconnect' that survives the known first-attempt E101 (OBS-01): retry on E101 only, log every retry in the
        transcript, and return the last reply. Anything else (or E101 on every attempt) is returned as it is, so the
        caller's assert still fails when the link really does not come back."""
        reply = None
        for attempt in range(1, attempts + 1):
            reply = self.exchange("reconnect", until=r"connected to|W114|E1\d\d", timeout=30)
            if not reply.has_code("E101"):
                break
            self.transcript.add("TX", f"<retry {attempt}/{attempts}: reconnect returned E101>")
            time.sleep(pause)
        return reply

    def wait_for_link(self, timeout: float = 45.0) -> bool:
        """Wait until the DUT has its Wi-Fi link, nudging it with 'reconnect' (the first attempt may give E101, OBS-01)."""

        def link_or_nudge() -> bool:
            if self.link_up():
                return True
            self.exchange("reconnect", until=r"connected to|W114|E1\d\d", timeout=20)
            return False

        return wait_until(link_or_nudge, timeout, interval=2.0) or self.link_up()

    def wait_for_internet(self, timeout: float = 40.0) -> bool:
        """Poll ``status`` until the DUT itself reports 'internet: OK' (its own check lags a few seconds behind the link)."""

        def internet_ok() -> bool:
            m = self.exchange("status", idle=0.8).search(r"internet:\s+(\w+)")
            return bool(m) and m.group(1).upper() == "OK"

        return wait_until(internet_ok, timeout, interval=3.0)

    def register(self, login: str, password: str) -> Response:
        return self.exchange(f"register {login} {password}", until=r"registered|E\d{3}", timeout=8)

    def login(self, login: str, password: str) -> Response:
        return self.exchange(f"login {login} {password}", until=r"on watch|E\d{3}", timeout=8)

    def login_waiting_out_lockout(self, login: str, password: str, max_wait: float = 40.0) -> Response:
        """Login, waiting out a lockout (E207/E210, 30 s) if the account is locked, so it does not cascade into the next test."""
        r = self.login(login, password)
        deadline = time.monotonic() + max_wait
        while ("E207" in r.codes or "E210" in r.codes) and time.monotonic() < deadline:
            m = r.search(r"Try again in (\d+) s")
            time.sleep((int(m.group(1)) if m else 5) + 1)
            r = self.login(login, password)
        return r

    def logout(self) -> Response:
        return self.exchange("logout")

    def close(self) -> None:
        self.transport.close()

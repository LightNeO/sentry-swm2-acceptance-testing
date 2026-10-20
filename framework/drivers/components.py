"""Component objects over the console: one class per device function (lamp, relay, guard, alerts).

They are thin on purpose: every method sends exactly one console command and returns the ``Response``, so the
assertions stay in the tests. What they remove is the command strings and the timing details (idle/timeout) from
the test bodies, the same job page objects do for a web UI. ``SwmDevice`` exposes them as ``dut.lamp``,
``dut.relay``, ``dut.guard`` and ``dut.alerts``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from drivers.protocol import Response

if TYPE_CHECKING:
    from drivers.device_driver import SwmDevice

DEFAULT_PIN = "1234"


class _Component:
    def __init__(self, dev: SwmDevice) -> None:
        self._dev = dev

    def _run(self, command: str, **kw) -> Response:
        return self._dev.exchange(command, **kw)


class Lamp(_Component):
    def on(self) -> Response:
        return self._run("lamp on")

    def off(self) -> Response:
        return self._run("lamp off")

    def status(self) -> Response:
        return self._run("lamp status")

    def set_color(self, color: str) -> Response:
        return self._run(f"lamp color {color}")

    def set_brightness(self, percent: int) -> Response:
        return self._run(f"lamp brightness {percent}")

    def set_mode(self, mode: str) -> Response:
        return self._run(f"lamp mode {mode}")

    def save_scene(self, slot: int) -> Response:
        return self._run(f"lamp scene save {slot}")

    def load_scene(self, slot: int) -> Response:
        return self._run(f"lamp scene load {slot}")


class Relay(_Component):
    def on(self, **kw) -> Response:
        return self._run("relay on", **kw)

    def off(self, **kw) -> Response:
        return self._run("relay off", **kw)

    def status(self) -> Response:
        return self._run("relay status")

    def health(self) -> Response:
        return self._run("relay health")

    def auto(self, enabled: bool) -> Response:
        return self._run(f"relay auto {'on' if enabled else 'off'}")

    def schedule(self, on_s: int, off_s: int) -> Response:
        return self._run(f"relay schedule {on_s} {off_s}")

    def stop_schedule(self) -> Response:
        return self._run("relay schedule off")


class Guard(_Component):
    """SENTRY Guard (firmware >= 2.3.0)."""

    def status(self) -> Response:
        return self._run("guard status")

    def arm(self, **kw) -> Response:
        return self._run("guard arm", **kw)

    def disarm(self, pin: str = DEFAULT_PIN, **kw) -> Response:
        return self._run(f"guard disarm {pin}", **kw)

    def change_pin(self, old: str, new: str, **kw) -> Response:
        return self._run(f"guard pin {old} {new}", **kw)

    def set_zone(self, cm: int) -> Response:
        return self._run(f"guard zone {cm}")

    def panic(self, **kw) -> Response:
        return self._run("guard panic", **kw)

    def log(self, **kw) -> Response:
        return self._run("guard log", **kw)


class Alerts(_Component):
    def list(self) -> Response:
        return self._run("alert list")

    def test(self, level: str = "", **kw) -> Response:
        return self._run(f"alert test {level}".rstrip(), **kw)

    def ack(self, alert_id: str | int | None = None) -> Response:
        """Acknowledge one alert by id, or the last one when no id is given."""
        return self._run("alert ack" if alert_id is None else f"alert ack {alert_id}")

    def ack_all(self) -> Response:
        return self._run("alert ack all", idle=0.8)

    def clear(self) -> Response:
        return self._run("alert clear", idle=0.8)

    def reset(self) -> None:
        """Acknowledge and clear everything, so the next test starts from an empty list."""
        self.ack_all()
        self.clear()


class Sonar(_Component):
    def measure(self, count: int | None = None, **kw) -> Response:
        return self._run("distance" if count is None else f"distance {count}", **kw)

    def calibrate(self, reference_cm: int, **kw) -> Response:
        return self._run(f"distance calibrate {reference_cm}", **kw)

    def calibrate_reset(self) -> Response:
        return self._run("distance calibrate reset")

    def set_alarm(self, cm: int) -> Response:
        return self._run(f"distance alarm {cm}")

    def alarm_off(self) -> Response:
        return self._run("distance alarm off")

    def set_filter(self, enabled: bool) -> Response:
        return self._run(f"distance filter {'on' if enabled else 'off'}")

    def stats(self) -> Response:
        return self._run("distance stats")

    def history(self) -> Response:
        return self._run("distance history")


class Ota(_Component):
    def install(self, version: str, **kw) -> Response:
        return self._run(f"ota install {version}", **kw)

    def set_url(self, url: str = "") -> Response:
        return self._run(f"ota url {url}".rstrip())

    def server(self) -> Response:
        return self._run("ota server")


class Wifi(_Component):
    def net(self) -> Response:
        return self._run("net")

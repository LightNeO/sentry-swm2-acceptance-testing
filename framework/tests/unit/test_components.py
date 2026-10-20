"""Component objects send the right console command and hand back the reply, so tests do not build command strings."""

import pytest

from drivers.device_driver import SwmDevice
from drivers.protocol import ErrorCode
from drivers.redaction import Redactor
from drivers.transport import FakeTransport

pytestmark = pytest.mark.unit


def make(script) -> tuple[SwmDevice, FakeTransport]:
    t = FakeTransport(script)
    return SwmDevice(t, Redactor(), timeout=1.0, idle=0.05), t


def test_lamp_commands():
    dev, t = make({})
    dev.lamp.on()
    dev.lamp.off()
    dev.lamp.set_color("red")
    dev.lamp.set_brightness(60)
    dev.lamp.set_mode("blink")
    dev.lamp.save_scene(1)
    dev.lamp.load_scene(2)
    dev.lamp.status()
    assert t.sent == [
        "lamp on",
        "lamp off",
        "lamp color red",
        "lamp brightness 60",
        "lamp mode blink",
        "lamp scene save 1",
        "lamp scene load 2",
        "lamp status",
    ]


def test_relay_commands():
    dev, t = make({})
    dev.relay.on()
    dev.relay.off()
    dev.relay.auto(True)
    dev.relay.auto(False)
    dev.relay.schedule(2, 3)
    dev.relay.stop_schedule()
    dev.relay.status()
    dev.relay.health()
    assert t.sent == [
        "relay on",
        "relay off",
        "relay auto on",
        "relay auto off",
        "relay schedule 2 3",
        "relay schedule off",
        "relay status",
        "relay health",
    ]


def test_guard_commands_default_to_the_documented_pin():
    dev, t = make({})
    dev.guard.arm()
    dev.guard.disarm()
    dev.guard.disarm("0000")
    dev.guard.change_pin("1234", "4321")
    dev.guard.set_zone(80)
    dev.guard.panic()
    dev.guard.log()
    dev.guard.status()
    assert t.sent == [
        "guard arm",
        "guard disarm 1234",
        "guard disarm 0000",
        "guard pin 1234 4321",
        "guard zone 80",
        "guard panic",
        "guard log",
        "guard status",
    ]


def test_alerts_reset_acknowledges_then_clears():
    dev, t = make({})
    dev.alerts.reset()
    assert t.sent == ["alert ack all", "alert clear"]


def test_component_returns_the_response_so_the_test_can_assert_on_it():
    dev, _ = make({"guard disarm 1234": "W (1) sentry: W802 not armed\n"})
    r = dev.guard.disarm()
    assert r.has_code(ErrorCode.W802)
    assert r.has_code("W802")  # the enum is a plain string, both spellings work
    assert not r.has_code(ErrorCode.E803)


def test_options_are_passed_through_to_exchange():
    dev, _ = make({"guard arm": "I (1) sentry: [WATCH] arming\n"})
    r = dev.guard.arm(idle=0.01, timeout=0.5)
    assert r.has("arming") and not r.timed_out

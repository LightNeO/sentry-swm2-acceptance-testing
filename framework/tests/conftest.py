"""Fixtures shared by several test folders (functional and hil)."""

import pytest

from drivers.components import DEFAULT_PIN


@pytest.fixture
def guard_clean(dut):
    """Guard disarmed, PIN back to the documented default, zone back to default 50 cm, no leftover alerts."""
    dut.guard.disarm(idle=0.8)  # ignore result: may already be disarmed
    if "disarmed" not in dut.guard.status().text:
        # PIN may not be the default from a previous test; try the two PINs this suite ever sets.
        for pin in ("4321", "0000", DEFAULT_PIN):
            dut.guard.disarm(pin, idle=0.8)
    dut.guard.change_pin(DEFAULT_PIN, DEFAULT_PIN, idle=0.8)  # no-op if already default; ignore E803
    dut.guard.set_zone(50)
    dut.alerts.reset()  # isolate from CIC alerts left by earlier Guard/Alert tests
    yield dut
    dut.guard.disarm(idle=0.8)

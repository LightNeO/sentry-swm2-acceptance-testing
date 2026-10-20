"""Fixtures shared by several test folders (functional and hil)."""

import pytest

from tests.helpers import DEFAULT_PIN


@pytest.fixture
def guard_clean(dut):
    """Guard disarmed, PIN back to the documented default, zone back to default 50 cm, no leftover alerts."""
    dut.exchange("guard disarm " + DEFAULT_PIN, idle=0.8)  # ignore result: may already be disarmed
    r = dut.exchange("guard status")
    if "disarmed" not in r.text:
        # PIN may not be the default from a previous test; try the two PINs this suite ever sets.
        for pin in ("4321", "0000", DEFAULT_PIN):
            dut.exchange(f"guard disarm {pin}", idle=0.8)
    dut.exchange(f"guard pin {DEFAULT_PIN} {DEFAULT_PIN}", idle=0.8)  # no-op if already default; ignore E803
    dut.exchange("guard zone 50")
    dut.exchange("alert ack all", idle=0.8)
    dut.exchange("alert clear", idle=0.8)  # isolate from CIC alerts left by earlier Guard/Alert tests
    yield dut
    dut.exchange("guard disarm " + DEFAULT_PIN, idle=0.8)

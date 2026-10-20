"""Fixtures for the functional (UART-only) suite."""

import pytest


@pytest.fixture
def clean_account(dut_raw, settings):
    """Unlock + reset attempt counter before a lockout test, in case a previous one left it locked."""
    r = dut_raw.login_waiting_out_lockout(settings.login, settings.password)
    assert "on watch" in r.text, f"cannot unlock the account:\n{r}"
    dut_raw.logout()
    return dut_raw


@pytest.fixture
def alerts_clean(dut):
    """Start with an empty, fully acknowledged alert list."""
    dut.alerts.reset()
    assert dut.alerts.list().has("no alerts")
    yield dut
    dut.alerts.reset()


@pytest.fixture
def guard_fresh(guard_clean, reboot_dut, settings):
    """Guard test that starts with a rebooted board, so the wrong-PIN counter does not carry over from earlier tests."""
    reboot_dut()
    guard_clean.login_waiting_out_lockout(settings.login, settings.password)
    return guard_clean

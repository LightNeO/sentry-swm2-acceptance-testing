"""The DUT for hardware tests.

Fixture chain: settings (once) -> device_session (once) -> dut_raw (baseline, per test) -> dut (+logged in).
"""

from __future__ import annotations

import os

import pytest

from drivers.config import Settings
from drivers.device_driver import SwmDevice, has_saved_network
from drivers.redaction import Redactor
from drivers.transport import SerialTransport, find_port
from swm_plugins.evidence import write_transcript
from swm_plugins.state import FW_KEY

INTERNET_WAIT_S = 40.0


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings.from_env()


@pytest.fixture(scope="session")
def device_session(request: pytest.FixtureRequest, settings: Settings):
    """Open the DUT once per run, bring it to: Wi-Fi up, profile registered, logged out."""
    port = os.environ.get("SWM_PORT") or find_port()
    redactor = Redactor([settings.wifi_password])
    device = SwmDevice(SerialTransport(port), redactor)
    try:
        boot = device.hard_reset()
        version = device.version()
        request.config.stash[FW_KEY] = "".join(version.split(".")[:2])  # "2.1.0" -> "21"
        if not has_saved_network(boot.text) and not (settings.ssid and settings.wifi_password):
            pytest.fail("DUT has no saved Wi-Fi network: set WIFI_SSID and WIFI_PASSWORD in framework/.env")
        wifi = device.ensure_wifi(boot.text, settings.ssid, settings.wifi_password)
        if set(wifi.errors) == {"E105"} and "connected to" in wifi.text:
            # E105 right after 'connected' is the internet check not finished yet: wait for it instead of ignoring it.
            if not device.wait_for_internet(INTERNET_WAIT_S):
                pytest.fail(f"Wi-Fi is up but there is no internet for {INTERNET_WAIT_S:.0f} s (E105)\n{wifi.text}")
        elif wifi.timed_out or wifi.errors:
            pytest.fail(f"Wi-Fi bring-up failed: {wifi.errors or 'timeout'}\n{wifi.text}")
        reg = device.register(settings.login, settings.password)
        if reg.errors and not reg.has_code("E202"):  # E202: profile already exists, which is fine
            pytest.fail(f"register failed: {reg.errors}\n{reg.text}")
        device.boot_text = boot.text
        device.fw_version = version
        yield device
    finally:
        try:
            device.logout()
        finally:
            device.close()


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def _restore_baseline(device: SwmDevice, settings: Settings) -> None:
    """Get back to baseline: logged out, NORMAL, lamp/relay off, Wi-Fi up. Reboot if stuck (EMERGENCY/hang)."""
    r = device.logout()
    stuck = r.timed_out or any(c in r.codes for c in ("E001", "E005", "E304"))
    if stuck:
        boot = device.reboot()
        device.ensure_wifi(boot.text, settings.ssid, settings.wifi_password)
    elif not device.link_up():  # test may have dropped Wi-Fi or rebooted the board
        device.ensure_wifi("known network", settings.ssid, settings.wifi_password)


@pytest.fixture
def dut_raw(request: pytest.FixtureRequest, device_session: SwmDevice, settings: Settings):
    """DUT at baseline, NOT logged in. For access-control and login tests."""
    version = _version_tuple(device_session.fw_version)
    if request.node.get_closest_marker("since_2_3_0") and version < (2, 3, 0):
        pytest.skip("requires firmware >= 2.3.0")
    if request.node.get_closest_marker("only_2_1_0") and version != (2, 1, 0):
        pytest.skip("applies to firmware 2.1.0 only")
    _restore_baseline(device_session, settings)
    device_session.transcript.clear()
    yield device_session
    write_transcript(request, device_session)
    _restore_baseline(device_session, settings)  # safe state for the next test: lamp/relay off, logged out


@pytest.fixture
def reboot_dut(device_session: SwmDevice, settings: Settings):
    """Callable: soft-reboot (not RTS - keeps Wi-Fi reliable), bring Wi-Fi back up, return the boot log."""

    def _reboot():
        boot = device_session.reboot()
        device_session.ensure_wifi(boot.text, settings.ssid, settings.wifi_password)
        return boot

    return _reboot


@pytest.fixture
def dut(dut_raw: SwmDevice, settings: Settings):
    """dut_raw, but logged in as the test user."""
    r = dut_raw.login_waiting_out_lockout(settings.login, settings.password)
    if "on watch" not in r.text:
        pytest.fail(f"Cannot log in for the test: {r.codes}\n{r.text}")
    return dut_raw

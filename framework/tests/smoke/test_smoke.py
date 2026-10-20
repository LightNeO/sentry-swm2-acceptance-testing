"""Smoke: is the DUT alive, identifiable and answering basic commands? Run first; if smoke fails, nothing else is meaningful."""

import re

import pytest

pytestmark = [pytest.mark.smoke]


@pytest.mark.tc("TC-SYS-05")
def test_boot_log_has_identity_and_reset_reason(device_session):
    boot = device_session.boot_text
    assert "ready. state 1 NORMAL" in boot
    assert re.search(r"fw v\d+\.\d+\.\d+", boot)
    assert re.search(r"last reset: (power on|software reboot|PANIC|watchdog|brownout)", boot)


@pytest.mark.tc("TC-OTA-01")
def test_version_format_matches_prd(dut_raw):
    r = dut_raw.exchange("version")
    assert r.search(r"SENTRY SWM-2 sonar watch module, fw v\d+\.\d+\.\d+ \(build .+\)")
    assert r.search(r"partition: ota_[01] @ 0x[0-9a-fA-F]+, state: valid")


@pytest.mark.tc("TC-OTA-01", "TC-OTA-32")
def test_version_same_in_boot_log_version_and_ota(dut):
    """OTA-1: the version number must be identical in the boot log, 'version' and 'ota'."""
    in_boot = re.search(r"fw v(\d+\.\d+\.\d+)", dut.boot_text).group(1)
    in_version = dut.exchange("version").search(r"fw v(\d+\.\d+\.\d+)").group(1)
    ota = dut.exchange("ota", until=r"E\d{3}|previous|partition", timeout=8)
    in_ota = ota.search(r"v(\d+\.\d+\.\d+)")
    assert in_ota, f"'ota' output has no version:\n{ota}"
    assert in_boot == in_version == in_ota.group(1)


@pytest.mark.tc("TC-SYS-01")
def test_help_lists_command_groups_and_access_marks(dut_raw):
    r = dut_raw.exchange("help", idle=1.0, timeout=8)
    for group in ("System:", "Buoy link (Wi-Fi):", "Account:", "States:", "OTA:", "Active sonar", "Telemetry"):
        assert r.has(group), f"help has no group {group!r}"
    assert r.has("[wifi]") and r.has("[login]")


@pytest.mark.tc("TC-AU-17")
def test_whoami_reports_user_access(dut, settings):
    r = dut.exchange("whoami")
    assert r.search(rf"user: {settings.login}, access: user")


@pytest.mark.tc("TC-AC-03")
def test_protected_command_without_login_is_rejected(dut_raw):
    assert dut_raw.exchange("lamp on").has_code("E003")

"""Wi-Fi connection and lifecycle cases on the managed SENTRY-HIL AP."""

from __future__ import annotations

import re

import pytest

pytestmark = pytest.mark.managed_wifi


def _connect(dut, ssid_or_number: str, password: str):
    """Drive the same interactive flow as a person at the UART console."""
    parts = [dut.exchange("connect", until=r"SSID or number:", timeout=10)]
    parts.append(dut.exchange(ssid_or_number, until=r"Password:|E1\d\d", timeout=5))
    parts.append(dut.exchange(password, secret=True, until=r"connected to|E1\d\d", timeout=45))
    return "\n".join(part.text for part in parts)


def _connect_by_scanned_number(dut, ssid: str, password: str):
    scan = dut.exchange("connect", until=r"SSID or number:", timeout=10)
    match = re.search(rf"\[\s*(\d+)\]\s+{re.escape(ssid)}\s+", scan.text)
    assert match, f"SSID {ssid!r} was not in scan output:\n{scan.text}"
    selected = dut.exchange(match.group(1), until=r"Password:|E1\d\d", timeout=5)
    password_result = dut.exchange(password, secret=True, until=r"connected to|E1\d\d", timeout=45)
    return "\n".join(part.text for part in (scan, selected, password_result))


@pytest.mark.tc("TC-WF-01")
def test_connect_by_ap_number(dut_raw, settings, managed_ap):
    text = _connect_by_scanned_number(dut_raw, settings.ssid, settings.wifi_password)
    assert "got ip" in text or "connected to" in text, text
    assert settings.ssid in text, text


@pytest.mark.tc("TC-WF-02")
def test_connect_by_ap_name(dut_raw, settings, managed_ap):
    text = _connect(dut_raw, settings.ssid, settings.wifi_password)
    assert "connected to" in text, text
    assert "got ip" in text, text


@pytest.mark.tc("TC-WF-03")
def test_short_wifi_password_is_rejected(dut_raw, settings, managed_ap):
    try:
        text = _connect(dut_raw, settings.ssid, "short7")
        assert "E112" in text
    finally:
        _connect(dut_raw, settings.ssid, settings.wifi_password)


@pytest.mark.tc("TC-WF-05")
def test_saved_network_is_reported_after_reboot(dut, reboot_dut, settings, managed_ap):
    boot = reboot_dut()
    assert f"known network '{settings.ssid}'" in boot.text
    assert "Type 'reconnect'" in boot.text


@pytest.mark.tc("TC-WF-04")
def test_empty_ssid_is_rejected(dut_raw, managed_ap):
    dut_raw.exchange("connect", until=r"SSID or number:", timeout=10)
    result = dut_raw.exchange("", timeout=5)
    assert result.has_code("E111"), result


@pytest.mark.tc("TC-WF-06")
def test_wrong_password_is_rejected(dut_raw, settings, managed_ap):
    try:
        text = _connect(dut_raw, settings.ssid, "WrongPass123")
        assert "E101" in text
    finally:
        _connect(dut_raw, settings.ssid, settings.wifi_password)


@pytest.mark.tc("TC-WF-07")
def test_unknown_ssid_is_rejected(dut_raw, settings, managed_ap):
    try:
        text = _connect(dut_raw, settings.ssid + "-NOT-FOUND", settings.wifi_password)
        assert "E102" in text
    finally:
        _connect(dut_raw, settings.ssid, settings.wifi_password)


@pytest.mark.tc("TC-WF-10")
def test_reconnect_without_saved_network_gives_e113(dut_raw, managed_ap, settings):
    dut_raw.exchange("forget", idle=1.0)
    try:
        assert dut_raw.exchange("reconnect").has_code("E113")
    finally:
        _connect(dut_raw, settings.ssid, settings.wifi_password)


@pytest.mark.tc("TC-WF-11")
def test_reconnect_after_disconnect_restores_link(dut_raw, settings, managed_ap):
    dut_raw.exchange("disconnect", idle=1.0)
    result = dut_raw.reconnect_with_retries()  # E101 is retried (OBS-01) but never counts as success
    assert result.search(r"connected to"), result


@pytest.mark.tc("TC-WF-12")
def test_forget_removes_saved_network_from_next_boot(dut_raw, settings, managed_ap):
    dut_raw.exchange("forget", idle=1.0)
    try:
        # Plain reboot: the reboot_dut fixture would bring Wi-Fi back and save the network again.
        boot = dut_raw.reboot()
        assert "known network '" not in boot.text
        assert dut_raw.exchange("reconnect").has_code("E113")
    finally:
        _connect(dut_raw, settings.ssid, settings.wifi_password)


@pytest.mark.tc("TC-WF-13")
def test_second_disconnect_is_warning(dut_raw, managed_ap):
    first = dut_raw.exchange("disconnect", idle=1.0)
    second = dut_raw.exchange("disconnect")
    assert not first.has_code("E001")
    assert second.has_code("W115")


@pytest.mark.tc("TC-WF-14")
def test_scan_sees_managed_ap(dut_raw, managed_ap, stand):
    result = dut_raw.exchange("scan", idle=3.5, timeout=10)
    assert stand.ap_connection in result.text


@pytest.mark.tc("TC-WF-16")
def test_ping_reaches_upstream(dut, managed_ap):
    result = dut.exchange("ping 1.1.1.1", timeout=15)
    assert not result.has_code("E002")
    assert not result.has_code("E001")


@pytest.mark.tc("TC-WF-17")
def test_time_is_available_after_managed_ap_connect(dut, managed_ap):
    result = dut.exchange("time", timeout=10)
    assert not result.has_code("E001")
    assert not result.has_code("E002")

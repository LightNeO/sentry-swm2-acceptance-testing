"""Settings keep secrets out of repr; StandConfig reads the stand from the environment."""

import pytest

from drivers.config import Settings, StandConfig

pytestmark = pytest.mark.unit


def test_settings_repr_hides_every_secret():
    s = Settings(login="qa", password="hunter2", ssid="HomeNet", wifi_password="s3cret-wifi")
    text = repr(s) + str(s)
    for secret in ("hunter2", "HomeNet", "s3cret-wifi"):
        assert secret not in text


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("TEST_LOGIN", "somebody")
    monkeypatch.setenv("WIFI_SSID", "net")
    s = Settings.from_env()
    assert s.login == "somebody" and s.ssid == "net"


def test_stand_config_defaults_and_overrides(monkeypatch):
    for name in ("HIL_AP_CONNECTION", "HIL_AP_ADDRESS", "HIL_OTA_PORT", "HIL_UPSTREAM_CONNECTION"):
        monkeypatch.delenv(name, raising=False)
    stand = StandConfig.from_env()
    assert (stand.ap_connection, stand.ap_address, stand.ota_port, stand.upstream_connection) == ("SENTRY-HIL", "10.42.0.1", 53317, "")

    monkeypatch.setenv("HIL_OTA_PORT", "8080")
    monkeypatch.setenv("HIL_UPSTREAM_CONNECTION", "uplink")
    stand = StandConfig.from_env()
    assert stand.ota_port == 8080 and stand.upstream_connection == "uplink"

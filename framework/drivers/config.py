"""Test configuration: .env loading and typed settings. Secrets are kept out of every repr (pytest prints
fixture arguments on a failure, and the Wi-Fi password must not leak that way)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

FRAMEWORK_DIR = Path(__file__).resolve().parents[1]


def load_env() -> None:
    """Load framework/.env into os.environ; real environment variables still win."""
    path = FRAMEWORK_DIR / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    """Test account and the Wi-Fi network the DUT is brought up on."""

    login: str
    password: str = field(repr=False)
    ssid: str = field(repr=False)
    wifi_password: str = field(repr=False)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            login=os.environ.get("TEST_LOGIN", "qa_swm"),
            password=os.environ.get("TEST_PASSWORD", "Pass1234"),
            ssid=os.environ.get("WIFI_SSID", ""),
            wifi_password=os.environ.get("WIFI_PASSWORD", ""),
        )


@dataclass(frozen=True)
class StandConfig:
    """HIL stand (Linux laptop): NetworkManager profiles/interfaces and where the OTA server is reachable."""

    ap_connection: str
    ap_interface: str
    upstream_connection: str
    upstream_interface: str
    ap_address: str
    ota_port: int

    @classmethod
    def from_env(cls) -> "StandConfig":
        return cls(
            ap_connection=os.environ.get("HIL_AP_CONNECTION", "SENTRY-HIL"),
            ap_interface=os.environ.get("HIL_AP_INTERFACE", "wlp1s0"),
            upstream_connection=os.environ.get("HIL_UPSTREAM_CONNECTION", ""),
            upstream_interface=os.environ.get("HIL_UPSTREAM_INTERFACE", "wlp0s21f0u2"),
            ap_address=os.environ.get("HIL_AP_ADDRESS", "10.42.0.1"),
            ota_port=int(os.environ.get("HIL_OTA_PORT", "53317")),
        )

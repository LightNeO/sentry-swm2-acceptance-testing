from __future__ import annotations

import os

import pytest

from drivers.managed_ap import ManagedAp


@pytest.fixture(autouse=True)
def wifi_baseline(device_session, settings) -> ManagedAp:
    controller = ManagedAp()
    controller.ensure_baseline()
    if not device_session.link_up():
        device_session.ensure_wifi("known network", settings["ssid"], settings["wifi_password"])
    try:
        yield controller
    finally:
        controller.cleanup()
        if not device_session.link_up():
            device_session.ensure_wifi("known network", settings["ssid"], settings["wifi_password"])


@pytest.fixture
def managed_ap(wifi_baseline: ManagedAp) -> ManagedAp:
    return wifi_baseline


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Require the explicit opt-in for all tests in this directory."""
    if config.getoption("--run-managed-wifi") and os.environ.get("HIL_AP_CONNECTION"):
        return
    skip = pytest.mark.skip(reason="managed Wi-Fi tests require --run-managed-wifi and HIL_AP_CONNECTION")
    for item in items:
        if "tests/wifi/" in item.nodeid:
            item.add_marker(skip)

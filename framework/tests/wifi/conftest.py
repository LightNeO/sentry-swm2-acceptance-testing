from __future__ import annotations

import os

import pytest

from drivers.managed_ap import ManagedAp


@pytest.fixture
def managed_ap() -> ManagedAp:
    controller = ManagedAp()
    controller.ensure_baseline()
    try:
        yield controller
    finally:
        controller.cleanup()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Require the explicit opt-in for all tests in this directory."""
    if config.getoption("--run-managed-wifi") and os.environ.get("HIL_AP_CONNECTION"):
        return
    skip = pytest.mark.skip(reason="managed Wi-Fi tests require --run-managed-wifi and HIL_AP_CONNECTION")
    for item in items:
        if "tests/wifi/" in item.nodeid:
            item.add_marker(skip)

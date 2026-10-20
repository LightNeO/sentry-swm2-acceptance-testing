"""Opt-in stand stages: they drive real hardware (Arduino) or toggle the laptop's network."""

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--run-hil", action="store_true", help="run the physical Arduino/DUT HIL stage")
    parser.addoption("--run-managed-wifi", action="store_true", help="run the destructive NetworkManager Wi-Fi stage")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    run_hil = config.getoption("--run-hil")
    run_wifi = config.getoption("--run-managed-wifi") and os.environ.get("HIL_AP_CONNECTION")
    skip_hil = pytest.mark.skip(reason="physical HIL stage requires --run-hil")
    skip_wifi = pytest.mark.skip(reason="managed Wi-Fi stage requires --run-managed-wifi and HIL_AP_CONNECTION")
    for item in items:
        if not run_hil and item.get_closest_marker("hil_stage"):
            item.add_marker(skip_hil)
        if not run_wifi and item.get_closest_marker("managed_wifi"):
            item.add_marker(skip_wifi)

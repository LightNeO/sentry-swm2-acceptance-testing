"""Fixtures for the Arduino HIL stage."""

import os

import pytest

from drivers.button_stimulator import ButtonStimulator


@pytest.fixture
def stimulator():
    """The Arduino Nano that presses K1-K4 (port in BUTTON_STIM_PORT)."""
    if not os.environ.get("BUTTON_STIM_PORT"):
        pytest.skip("set BUTTON_STIM_PORT to run the physical button stage")
    with ButtonStimulator() as stimulator:
        yield stimulator

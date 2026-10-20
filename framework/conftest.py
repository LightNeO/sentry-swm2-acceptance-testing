"""pytest entry point: loads framework/.env and the framework plugins.

swm_plugins/stages.py    opt-in HIL and managed Wi-Fi stages (--run-hil, --run-managed-wifi)
swm_plugins/evidence.py  transcripts (--keep-logs) and results.json recording (--record)
swm_plugins/device.py    settings, device_session -> dut_raw -> dut, reboot_dut
Folder-specific fixtures live in tests/**/conftest.py. Unit tests do not use any hardware fixture.
"""

from drivers.config import load_env

load_env()

pytest_plugins = ["swm_plugins.stages", "swm_plugins.evidence", "swm_plugins.device"]

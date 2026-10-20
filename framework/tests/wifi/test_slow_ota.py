"""TC-OTA-16: the Wi-Fi access point disappears in the middle of an OTA download (slow local server).

Stand notes: the OTA server runs on the stand laptop (Linux), reached through the test AP (StandConfig: HIL_AP_ADDRESS,
HIL_OTA_PORT) on a port the firewall allows (see tests/wifi/conftest.py, fixture slow_ota_server). The image is the one the board already runs, so
the run never downgrades (W409 'same version - reinstalling' is expected) and is interrupted long before it finishes.
Server files are not in git: `python fw_7/tools/ota_server.py --download` fetches them.
"""

from __future__ import annotations

import re

import pytest

pytestmark = pytest.mark.managed_wifi


def _running_image(dut) -> str:
    """'fw v2.3.0 ... partition: ota_1' from `version`: which image the board runs and from which slot."""
    text = dut.exchange("version", idle=0.8).text
    fw = re.search(r"fw v([\d.]+)", text)
    part = re.search(r"partition: (ota_\d)", text)
    assert fw and part, f"cannot read the running image from 'version':\n{text}"
    assert "state: valid" in text, f"running image is not valid:\n{text}"
    return f"v{fw.group(1)} {part.group(1)}"


@pytest.mark.tc("TC-OTA-16")
def test_ap_loss_during_slow_ota_download_is_survived(dut, managed_ap, slow_ota_server):
    dut.wait_for_link()
    if not dut.wait_for_internet(60):
        # Seen in the evidence run 3: the stand's upstream had not recovered yet, so the board never got internet.
        pytest.skip("precondition: the stand has no internet for the DUT before the test starts (check the upstream)")
    before = _running_image(dut)

    started = dut.exchange(f"ota url {slow_ota_server.image_url}", until=r"\[OTA\] downloading", timeout=20)
    assert not started.errors, started
    dut.wait_for(r"\[OTA\]\s+10%", timeout=60)

    managed_ap.ap_down()
    try:
        # One wait covers the whole reaction, so no line is lost between two waits:
        # W110 -> automatic reconnect attempts -> the download is reported as failed.
        reaction = dut.wait_for(r"E41[01] ", timeout=120).text
    finally:
        managed_ap.ap_up()
    assert "W110" in reaction, reaction
    assert "retry 1/3" in reaction, reaction

    assert dut.wait_for_link(), "DUT did not get its Wi-Fi link back after the access point returned"
    assert _running_image(dut) == before, "the interrupted download must not change the running image"

    assert dut.wait_for_internet(), "no internet after the access point returned"
    check = dut.exchange("ota check", until=r"E\d{3}|\[OTA\] stable", timeout=30)
    assert not check.errors, check

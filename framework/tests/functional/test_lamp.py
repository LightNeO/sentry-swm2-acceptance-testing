"""Smart Lamp: scenes, status/NVS persistence, repeated on/off (LM-1, LM-6, LM-7)."""

import pytest

from drivers.protocol import ErrorCode

pytestmark = [pytest.mark.functional]


@pytest.mark.tc("TC-LM-02")
def test_repeated_on_off_gives_w510(dut):
    dut.lamp.off()  # make sure we start OFF; lamp defaults off after login
    assert dut.lamp.off().has_code(ErrorCode.W510)
    dut.lamp.on()
    assert dut.lamp.on().has_code(ErrorCode.W510)
    dut.lamp.off()


@pytest.mark.tc("TC-LM-17")
def test_scene_save_load_round_trip(dut):
    dut.lamp.set_color("red")
    dut.lamp.set_brightness(60)
    dut.lamp.set_mode("blink")
    assert dut.lamp.save_scene(1).has("scene 1 saved")
    dut.lamp.set_color("blue")
    dut.lamp.set_brightness(10)
    dut.lamp.set_mode("solid")
    r = dut.lamp.load_scene(1)
    assert r.has("(255,0,0)") and r.has("60%") and r.has("blink"), r
    assert dut.lamp.status().has("color (255,0,0)")


@pytest.mark.tc("TC-LM-19")
def test_loading_empty_scene_gives_e509(dut):
    """Scene 2 is never saved by any other test, so it stays empty for this check."""
    r = dut.lamp.load_scene(2)
    assert r.has_code(ErrorCode.E509), r
    assert r.has("Use 'lamp scene save 2'")


@pytest.mark.tc("TC-LM-21")
@pytest.mark.persistence
def test_lamp_settings_survive_reboot_but_lamp_itself_turns_off(dut, reboot_dut, settings):
    """LM-1 (off after reboot) and LM-7 (NVS) together: the ON/OFF flag resets, the rest does not."""
    dut.lamp.set_color("green")
    dut.lamp.set_brightness(42)
    dut.lamp.set_mode("breathe")
    dut.lamp.on()
    reboot_dut()
    assert dut.login(settings.login, settings.password).has("on watch")
    r = dut.lamp.status()
    assert r.has("off,"), f"lamp must be OFF right after reboot:\n{r}"
    assert r.has("color (0,255,0)") and r.has("brightness 42%") and r.has("mode breathe"), f"color/brightness/mode must survive reboot:\n{r}"

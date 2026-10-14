"""Account: login attempts/lockout (AU-2), password change (AU-5), sudo (AU-6), logout (AU-3).

Tests that change the password restore it in 'finally' or every later test breaks. Lockout
doesn't cascade since 'dut' waits it out before logging in.
"""

import time

import pytest

from conftest import login_waiting_out_lockout
from tests.helpers import lockout_seconds

pytestmark = [pytest.mark.functional]


@pytest.fixture
def clean_account(dut_raw, settings):
    """Unlock + reset attempt counter before a lockout test, in case a previous one left it locked."""
    r = login_waiting_out_lockout(dut_raw, settings["login"], settings["password"])
    assert "on watch" in r.text, f"cannot unlock the account:\n{r}"
    dut_raw.logout()
    return dut_raw


def wrong_login(dut, settings, login=None):
    return dut.login(login or settings["login"], "WrongPass-1")


@pytest.mark.tc("TC-AU-02")
def test_second_profile_is_refused_with_e202(dut_raw):
    r = dut_raw.register("other_user", "Pass1234")
    assert r.has_code("E202"), f"codes {r.codes}\n{r}"


@pytest.mark.tc("TC-AU-08", "TC-AU-09")
@pytest.mark.slow
@pytest.mark.usefixtures("clean_account")
def test_three_wrong_passwords_lock_the_account_for_30_s(dut_raw, settings):
    r1 = wrong_login(dut_raw, settings)
    r2 = wrong_login(dut_raw, settings)
    assert r1.has_code("E209") and r1.has("Attempts: 1/3"), r1
    assert r2.has_code("E209") and r2.has("Attempts: 2/3"), r2
    r3 = wrong_login(dut_raw, settings)
    assert r3.has_code("E210") and r3.has("30 s"), r3
    locked_at = time.monotonic()

    r4 = dut_raw.login(settings["login"], settings["password"])  # even the CORRECT password is refused while locked
    assert r4.has_code("E207"), f"correct password must be refused during lockout:\n{r4}"
    assert 0 < (lockout_seconds(r4) or 0) <= 30, f"'Try again in N s' must count down from 30: {lockout_seconds(r4)}"

    while True:  # measure the real lockout length
        r = dut_raw.login(settings["login"], settings["password"])
        if "on watch" in r.text:
            break
        assert time.monotonic() - locked_at < 45, f"still locked after 45 s:\n{r}"
        time.sleep(1)
    elapsed = time.monotonic() - locked_at
    assert 28 <= elapsed <= 33, f"lockout must last ~30 s, lasted {elapsed:.1f} s"


@pytest.mark.tc("TC-AU-11")
@pytest.mark.slow
@pytest.mark.usefixtures("clean_account")
def test_lockout_counts_attempts_with_unknown_login_too(dut_raw, settings):
    """AU-2: the limit applies to ANY login typed into 'login', even one that does not exist."""
    rs = [wrong_login(dut_raw, settings, "no_such_user") for _ in range(3)]
    assert rs[2].has_code("E210"), f"3 attempts with a non-existent login must lock the account:\n{[r.codes for r in rs]}"
    assert dut_raw.login(settings["login"], settings["password"]).has_code("E207")


@pytest.mark.tc("TC-AU-12")
@pytest.mark.slow
@pytest.mark.usefixtures("clean_account")
def test_lockout_counts_mixed_logins_together(dut_raw, settings):
    wrong_login(dut_raw, settings)
    wrong_login(dut_raw, settings, "no_such_user")
    assert wrong_login(dut_raw, settings).has_code("E210")


@pytest.mark.tc("TC-AU-14")
@pytest.mark.usefixtures("clean_account")
def test_successful_login_resets_attempt_counter(dut_raw, settings):
    wrong_login(dut_raw, settings)
    wrong_login(dut_raw, settings)
    assert dut_raw.login(settings["login"], settings["password"]).has("on watch")
    dut_raw.logout()
    assert wrong_login(dut_raw, settings).has("Attempts: 1/3"), "counter must start from 1 again after a successful login"


@pytest.mark.tc("TC-AU-13")
def test_login_while_logged_in_gives_e206(dut, settings):
    assert dut.login(settings["login"], settings["password"]).has_code("E206")


@pytest.mark.tc("TC-AU-16")
def test_logout_without_session_gives_w211(dut_raw):
    assert dut_raw.logout().has_code("W211")


@pytest.mark.tc("TC-AU-17")
def test_whoami_before_login(dut_raw):
    r = dut_raw.exchange("whoami")
    assert not r.errors, r  # whoami is always available; exact text for 'no session' is not fixed by the PRD


@pytest.mark.tc("TC-AU-20")
def test_passwd_with_wrong_old_password_gives_e215(dut):
    assert dut.exchange("passwd WrongOld-1 Newpass99").has_code("E215")


@pytest.mark.tc("TC-AU-21")
@pytest.mark.parametrize(
    "length,error",
    [(5, "E205"), (6, None), (32, None), (33, "E205")],
)
def test_passwd_new_password_length_range(dut, settings, length, error):
    new = ("Ab1" * 20)[:length]
    old = settings["password"]
    r = dut.exchange(f"passwd {old} {new}")
    try:
        if error:
            assert r.has_code(error), f"length {length}: expected {error}, got {r.codes}\n{r}"
        else:
            assert not r.errors, f"length {length} must be accepted (6-32 inclusive), got {r.errors}\n{r}"
    finally:
        if not error and not r.errors:
            restore = dut.exchange(f"passwd {new} {old}")
            assert not restore.errors, f"could not restore the test password:\n{restore}"


@pytest.mark.tc("TC-AU-18", "TC-AU-19")
@pytest.mark.persistence
def test_changed_password_works_after_logout_and_reboot_old_one_does_not(dut, settings, reboot_dut):
    old, new = settings["password"], "NewPass99"
    assert not dut.exchange(f"passwd {old} {new}").errors
    try:
        dut.logout()
        assert dut.login(settings["login"], old).has_code("E209"), "OLD password must stop working right after passwd"
        assert dut.login(settings["login"], new).has("on watch"), "NEW password must work after logout"
        reboot_dut()
        assert dut.login(settings["login"], old).has_code("E209"), "old password must not return after reboot (AU-5: permanent)"
        assert dut.login(settings["login"], new).has("on watch"), "new password must survive reboot"
    finally:
        r = login_waiting_out_lockout(dut, settings["login"], new)
        if "on watch" in r.text or r.has_code("E206"):
            dut.exchange(f"passwd {new} {old}")
        else:  # the old password may still be valid if passwd did not persist
            login_waiting_out_lockout(dut, settings["login"], old)


@pytest.mark.tc("TC-AU-22")
def test_sudo_wrong_password_gives_e213_and_keeps_user_access(dut, settings):
    assert dut.exchange("sudo not-the-password").has_code("E213")
    assert dut.exchange("whoami").has("access: user")


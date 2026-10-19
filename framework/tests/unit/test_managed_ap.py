"""Unit tests for the host-side NetworkManager controller."""

import pytest

from drivers.managed_ap import ManagedAp, NetworkCommandError, NetworkSnapshot


pytestmark = pytest.mark.unit


class FakeRunner:
    def __init__(self):
        self.commands: list[list[str]] = []

    def run(self, args):
        self.commands.append(list(args))
        if args[:3] == ["nmcli", "-t", "-f"]:
            return "state\n"
        return "ok\n"


def test_ap_and_upstream_use_only_named_connections():
    runner = FakeRunner()
    ap = ManagedAp(runner, ap_connection="SENTRY-HIL", ap_interface="wlp1s0", upstream_connection="NeO", upstream_interface="wlp0s21f0u2")

    ap.ap_down()
    ap.upstream_down()

    ap_down = ["nmcli", "connection", "down", "SENTRY-HIL"]
    upstream_down = ["nmcli", "connection", "down", "NeO"]
    assert ap_down in runner.commands
    assert upstream_down in runner.commands
    assert runner.commands.index(ap_down) < runner.commands.index(upstream_down)


def test_baseline_does_not_restart_connections_that_are_already_active():
    class ActiveRunner(FakeRunner):
        def run(self, args):
            self.commands.append(list(args))
            if args[:6] == ["nmcli", "-t", "-f", "NAME", "connection", "show"]:
                return "NeO\nSENTRY-HIL\n"
            return "ok\n"

    runner = ActiveRunner()
    ManagedAp(runner, ap_connection="SENTRY-HIL", upstream_connection="NeO").ensure_baseline()

    assert not any(cmd[:3] == ["nmcli", "connection", "up"] for cmd in runner.commands)


def test_baseline_brings_up_only_the_connection_that_is_down():
    class OneDownRunner(FakeRunner):
        def run(self, args):
            self.commands.append(list(args))
            if args[:6] == ["nmcli", "-t", "-f", "NAME", "connection", "show"]:
                return "NeO\n"
            return "ok\n"

    runner = OneDownRunner()
    ManagedAp(runner, ap_connection="SENTRY-HIL", ap_interface="wlp1s0", upstream_connection="NeO").ensure_baseline()

    ups = [cmd for cmd in runner.commands if cmd[:3] == ["nmcli", "connection", "up"]]
    assert ups == [["nmcli", "connection", "up", "SENTRY-HIL", "ifname", "wlp1s0"]]


def test_snapshot_collects_three_host_views():
    runner = FakeRunner()
    ap = ManagedAp(runner)

    snapshot = ap.snapshot()

    assert isinstance(snapshot, NetworkSnapshot)
    assert len(runner.commands) == 3
    assert runner.commands[1] == ["ip", "-br", "addr"]
    assert runner.commands[2] == ["iw", "dev"]


def test_cleanup_does_not_raise_when_host_is_already_disconnected():
    class BrokenRunner(FakeRunner):
        def run(self, args):
            self.commands.append(list(args))
            raise NetworkCommandError("network unavailable")

    ManagedAp(BrokenRunner()).cleanup()

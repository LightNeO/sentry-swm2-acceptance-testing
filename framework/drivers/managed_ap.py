"""Small, explicit controller for the local SENTRY-HIL NetworkManager AP."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from drivers.config import StandConfig


class NetworkCommandError(RuntimeError):
    """A NetworkManager/ip/iw command failed."""


class CommandRunner:
    def run(self, args: Sequence[str]) -> str:
        completed = subprocess.run(args, text=True, capture_output=True, check=False)
        if completed.returncode:
            detail = (completed.stderr or completed.stdout).strip()
            raise NetworkCommandError(f"{' '.join(args)} failed: {detail}")
        return completed.stdout


@dataclass(frozen=True)
class NetworkSnapshot:
    devices: str
    addresses: str
    wifi: str


class ManagedAp:
    """Control only the named test AP and its upstream connection."""

    def __init__(
        self,
        runner: CommandRunner | None = None,
        *,
        ap_connection: str | None = None,
        ap_interface: str | None = None,
        upstream_connection: str | None = None,
        upstream_interface: str | None = None,
    ) -> None:
        stand = StandConfig.from_env()
        self.runner = runner or CommandRunner()
        self.ap_connection = ap_connection or stand.ap_connection
        self.ap_interface = ap_interface or stand.ap_interface
        self.upstream_connection = upstream_connection or stand.upstream_connection
        if not self.upstream_connection:
            raise ValueError("set HIL_UPSTREAM_CONNECTION to the NetworkManager profile of the stand's upstream network")
        self.upstream_interface = upstream_interface or stand.upstream_interface

    def snapshot(self) -> NetworkSnapshot:
        return NetworkSnapshot(
            devices=self.runner.run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device", "status"]),
            addresses=self.runner.run(["ip", "-br", "addr"]),
            wifi=self.runner.run(["iw", "dev"]),
        )

    def ap_up(self) -> NetworkSnapshot:
        self.runner.run(["nmcli", "connection", "up", self.ap_connection, "ifname", self.ap_interface])
        return self.snapshot()

    def ap_down(self) -> NetworkSnapshot:
        self.runner.run(["nmcli", "connection", "down", self.ap_connection])
        return self.snapshot()

    def upstream_up(self) -> NetworkSnapshot:
        self.runner.run(["nmcli", "connection", "up", self.upstream_connection, "ifname", self.upstream_interface])
        return self.snapshot()

    def upstream_down(self) -> NetworkSnapshot:
        """Drop only the upstream link; leave SENTRY-HIL AP and DHCP running."""
        self.runner.run(["nmcli", "connection", "down", self.upstream_connection])
        return self.snapshot()

    def active_connections(self) -> set[str]:
        out = self.runner.run(["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"])
        return {line.strip() for line in out.splitlines() if line.strip()}

    def ensure_baseline(self) -> NetworkSnapshot:
        """Bring up only what is down. 'nmcli connection up' on an active AP re-activates it, which drops the
        DUT's Wi-Fi (W110 reason 7) - seen on the stand as random link loss at the start of a test."""
        active = self.active_connections()
        if self.upstream_connection not in active:
            self.upstream_up()
        if self.ap_connection not in active:
            self.ap_up()
        return self.snapshot()

    def cleanup(self) -> None:
        """Best effort restore. Preserve the original error from a test."""
        try:
            self.ensure_baseline()
        except (NetworkCommandError, OSError):
            pass

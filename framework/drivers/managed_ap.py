"""Small, explicit controller for the local SENTRY-HIL NetworkManager AP."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Sequence


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
        self.runner = runner or CommandRunner()
        self.ap_connection = ap_connection or os.environ.get("HIL_AP_CONNECTION", "SENTRY-HIL")
        self.ap_interface = ap_interface or os.environ.get("HIL_AP_INTERFACE", "wlp1s0")
        self.upstream_connection = upstream_connection or os.environ.get("HIL_UPSTREAM_CONNECTION", "NeO")
        self.upstream_interface = upstream_interface or os.environ.get("HIL_UPSTREAM_INTERFACE", "wlp0s21f0u2")

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

    def ensure_baseline(self) -> NetworkSnapshot:
        self.upstream_up()
        return self.ap_up()

    def cleanup(self) -> None:
        """Best effort restore. Preserve the original error from a test."""
        try:
            self.ensure_baseline()
        except (NetworkCommandError, OSError):
            pass

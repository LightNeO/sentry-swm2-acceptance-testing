"""Runs fw_7/tools/ota_server.py as a child process, for OTA tests that need a slow or failing server.

Works the same on Linux and Windows (plain subprocess + a TCP readiness probe). The server itself serves files from
fw_7/tools/server_files/ (not in git: fetch once with `python fw_7/tools/ota_server.py --download`).
"""

from __future__ import annotations

import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_SCRIPT = REPO_ROOT / "fw_7" / "tools" / "ota_server.py"
FIRMWARE_DIR = REPO_ROOT / "fw_7" / "tools" / "server_files" / "fw7"


def firmware_available(version: str) -> bool:
    """True if the server has the image of this version (e.g. '2.3.0') to serve."""
    return (FIRMWARE_DIR / f"v{version}" / "sentry_fw7.bin").is_file()


class OtaServerProcess:
    def __init__(self, port: int, slow_kb_s: float = 0.0, script: Path | None = None) -> None:
        self.port = port
        self.slow_kb_s = slow_kb_s
        self.script = Path(script) if script else SERVER_SCRIPT
        self._proc: subprocess.Popen | None = None
        self._log = tempfile.TemporaryFile(mode="w+b")

    def start(self, ready_timeout: float = 10.0) -> None:
        cmd = [sys.executable, str(self.script), "--port", str(self.port)]
        if self.slow_kb_s:
            cmd += ["--slow", str(self.slow_kb_s)]
        self._proc = subprocess.Popen(cmd, stdout=self._log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + ready_timeout
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                raise RuntimeError(f"OTA server exited with code {self._proc.returncode}:\n{self.output()}")
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.2)
        self.stop()
        raise RuntimeError(f"OTA server did not listen on port {self.port} within {ready_timeout:.0f} s:\n{self.output()}")

    def output(self) -> str:
        self._log.flush()
        self._log.seek(0)
        return self._log.read().decode("utf-8", errors="replace")

    def stop(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    def __enter__(self) -> OtaServerProcess:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

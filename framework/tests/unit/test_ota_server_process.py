"""OtaServerProcess starts a child server, waits until it listens and stops it (checked with a stand-in script)."""

import socket

import pytest

from drivers.ota_server_process import OtaServerProcess

pytestmark = pytest.mark.unit

LISTENER = """
import socket, sys, time
port = int(sys.argv[sys.argv.index("--port") + 1])
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", port))
s.listen()
time.sleep(60)
"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def port_is_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


def test_server_is_reachable_while_running_and_gone_after_stop(tmp_path):
    script = tmp_path / "fake_server.py"
    script.write_text(LISTENER, encoding="utf-8")
    port = free_port()

    server = OtaServerProcess(port, slow_kb_s=20, script=script)
    server.start()
    try:
        assert port_is_open(port)
    finally:
        server.stop()
    assert not port_is_open(port)


def test_server_that_exits_at_once_is_reported_with_its_output(tmp_path):
    script = tmp_path / "broken_server.py"
    script.write_text("print('No firmware yet'); raise SystemExit(1)", encoding="utf-8")

    with pytest.raises(RuntimeError, match="No firmware yet"):
        OtaServerProcess(free_port(), script=script).start(ready_timeout=5)

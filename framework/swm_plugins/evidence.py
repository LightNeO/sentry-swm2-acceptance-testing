"""Evidence: per-test UART transcripts and PASS/FAIL recording into docs/results.json (for the traceability matrix)."""

from __future__ import annotations

import hashlib
import json
import re
import time

import pytest

from swm_plugins.state import FW_KEY, LOG_DIR, RESULTS_FILE, RESULTS_KEY


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--keep-logs", action="store_true", help="write a transcript for every test, not only failed ones")
    parser.addoption("--record", action="store_true", help="record PASS/FAIL per TC into docs/results.json (for traceability)")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Stash each phase's report on item.rep_<phase> (fixtures check this for pass/fail) and collect --record results."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
    if rep.when == "call" and item.config.getoption("--record") and item.config.stash.get(FW_KEY, None):
        bucket = item.config.stash.setdefault(RESULTS_KEY, {})
        for marker in item.iter_markers("tc"):
            for tc in marker.args:
                status = {"passed": "PASS", "failed": "FAIL"}.get(rep.outcome)
                if status:
                    old = bucket.get(tc)
                    bucket[tc] = "FAIL" if "FAIL" in (old, status) else status


def pytest_sessionfinish(session: pytest.Session) -> None:
    """Merge recorded statuses into docs/results.json (traceability.md gets regenerated from this later)."""
    config = session.config
    bucket = config.stash.get(RESULTS_KEY, None)
    fwkey = config.stash.get(FW_KEY, None)
    if not bucket or not fwkey:
        return
    data = json.loads(RESULTS_FILE.read_text(encoding="utf-8")) if RESULTS_FILE.exists() else {}
    for tc, status in bucket.items():
        data.setdefault(tc, {})[fwkey] = status
    RESULTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_transcript(request: pytest.FixtureRequest, device) -> None:
    """Save the UART transcript of the test (always with --keep-logs, otherwise only when the test failed)."""
    failed = getattr(request.node, "rep_call", None) is not None and request.node.rep_call.failed
    if not (failed or request.config.getoption("--keep-logs")):
        return
    folder = LOG_DIR / f"v{device.fw_version}"
    folder.mkdir(parents=True, exist_ok=True)
    raw_name = re.sub(r"[^\w.-]+", "_", request.node.nodeid.split("::", 1)[-1])
    digest = hashlib.sha1(raw_name.encode(), usedforsecurity=False).hexdigest()[:10]
    name = f"{raw_name[:100].rstrip('_')}_{digest}"
    header = f"# {request.node.nodeid}\n# fw v{device.fw_version}  {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    (folder / f"{name}.log").write_text(header + device.transcript.render(), encoding="utf-8")

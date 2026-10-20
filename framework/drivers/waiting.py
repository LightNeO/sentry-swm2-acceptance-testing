"""One polling helper for everything that has to wait for the hardware (link, internet, lockout...)."""

from __future__ import annotations

import time
from collections.abc import Callable


def wait_until(predicate: Callable[[], bool], timeout: float, interval: float = 1.0) -> bool:
    """Call ``predicate`` until it is true or ``timeout`` seconds passed; True if it became true (checked at least once)."""
    deadline = time.monotonic() + timeout
    while True:
        if predicate():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval)

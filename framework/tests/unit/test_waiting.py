"""wait_until: the one polling primitive."""

import pytest

from drivers.waiting import wait_until

pytestmark = pytest.mark.unit


def test_returns_true_as_soon_as_the_predicate_holds():
    calls = []

    def predicate():
        calls.append(1)
        return len(calls) == 3

    assert wait_until(predicate, timeout=5, interval=0.01)
    assert len(calls) == 3


def test_returns_false_after_the_timeout():
    assert not wait_until(lambda: False, timeout=0.05, interval=0.01)


def test_checks_at_least_once_even_with_zero_timeout():
    assert wait_until(lambda: True, timeout=0)

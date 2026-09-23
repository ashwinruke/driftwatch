import pytest

from driftwatch.retry import with_retry


def test_returns_result_on_first_success():
    def always_succeeds():
        return "ok"

    assert with_retry(always_succeeds, base_delay=0) == "ok"


def test_retries_then_succeeds():
    calls = {"count": 0}

    def fails_twice_then_succeeds():
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("transient")
        return "ok"

    result = with_retry(fails_twice_then_succeeds, max_attempts=3, base_delay=0)
    assert result == "ok"
    assert calls["count"] == 3


def test_raises_after_exhausting_attempts():
    def always_fails():
        raise ValueError("permanent")

    with pytest.raises(ValueError):
        with_retry(always_fails, max_attempts=2, base_delay=0)

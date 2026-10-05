from driftwatch.persistence.review_store import IN_FLIGHT_WINDOW_SECONDS, should_skip_review


def test_no_prior_run_proceeds():
    assert should_skip_review(None) is False


def test_completed_run_is_skipped():
    assert should_skip_review(("completed", 3600.0)) is True


def test_failed_run_is_retried():
    assert should_skip_review(("failed", 30.0)) is False


def test_recent_in_flight_run_is_skipped_as_duplicate():
    assert should_skip_review(("running", 10.0)) is True


def test_stale_in_flight_run_is_treated_as_crashed_and_retried():
    assert should_skip_review(("running", IN_FLIGHT_WINDOW_SECONDS + 1)) is False

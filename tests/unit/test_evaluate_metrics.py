from driftwatch.cli.evaluate import (
    FixtureResult,
    build_report,
    compute_confusion_matrix,
)


def _result(fixture="f", expected=True, candidates=0, accepted=0, rejected=0, needs_review=0, static_corroborated=0, latency=0.1):
    return FixtureResult(
        fixture=fixture, expected=expected, candidate_count=candidates,
        accepted_count=accepted, rejected_count=rejected,
        needs_review_count=needs_review, static_corroborated_count=static_corroborated,
        latency_seconds=latency,
    )


def test_confusion_matrix_true_positive():
    results = [_result(expected=True, accepted=1)]
    matrix = compute_confusion_matrix(results, lambda r: r.accepted_count)
    assert (matrix.tp, matrix.fp, matrix.fn, matrix.tn) == (1, 0, 0, 0)


def test_confusion_matrix_false_negative():
    results = [_result(expected=True, accepted=0)]
    matrix = compute_confusion_matrix(results, lambda r: r.accepted_count)
    assert (matrix.tp, matrix.fp, matrix.fn, matrix.tn) == (0, 0, 1, 0)


def test_confusion_matrix_false_positive():
    results = [_result(expected=False, accepted=1)]
    matrix = compute_confusion_matrix(results, lambda r: r.accepted_count)
    assert (matrix.tp, matrix.fp, matrix.fn, matrix.tn) == (0, 1, 0, 0)


def test_confusion_matrix_true_negative():
    results = [_result(expected=False, accepted=0)]
    matrix = compute_confusion_matrix(results, lambda r: r.accepted_count)
    assert (matrix.tp, matrix.fp, matrix.fn, matrix.tn) == (0, 0, 0, 1)


def test_precision_recall_f1_and_fpr():
    from driftwatch.cli.evaluate import ConfusionMatrix
    matrix = ConfusionMatrix(tp=3, fp=1, fn=1, tn=5)
    assert matrix.precision == 0.75
    assert matrix.recall == 0.75
    assert round(matrix.f1, 4) == 0.75
    assert matrix.false_positive_rate == 1 / 6


def test_empty_matrix_metrics_are_zero_not_error():
    from driftwatch.cli.evaluate import ConfusionMatrix
    matrix = ConfusionMatrix()
    assert matrix.precision == 0.0
    assert matrix.recall == 0.0
    assert matrix.f1 == 0.0
    assert matrix.false_positive_rate == 0.0


def test_before_validation_uses_raw_candidates_after_uses_accepted():
    # A finding that would have been posted before validation (any
    # candidate) but gets correctly filtered out after validation --
    # this is the concrete "before vs after" difference the report exists
    # to show.
    results = [_result(expected=False, candidates=1, accepted=0)]
    report = build_report(results)

    assert report.before.fp == 1  # before: posted a false positive
    assert report.after.tn == 1   # after: correctly rejected it


def test_static_analysis_agreement_rate_is_fraction_of_accepted():
    results = [
        _result(fixture="a", accepted=1, static_corroborated=1),
        _result(fixture="b", accepted=1, static_corroborated=0),
    ]
    report = build_report(results)
    assert report.static_analysis_agreement_rate == 0.5


def test_validation_acceptance_and_rejected_rates():
    results = [_result(candidates=4, accepted=2, rejected=1, needs_review=1)]
    report = build_report(results)
    assert report.validation_acceptance_rate == 0.5
    assert report.rejected_rate == 0.25


def test_no_fixtures_does_not_crash():
    report = build_report([])
    assert report.fixture_count == 0
    assert report.validation_acceptance_rate == 0.0
    assert report.average_latency_seconds == 0.0

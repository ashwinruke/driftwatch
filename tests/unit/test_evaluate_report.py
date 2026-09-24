from driftwatch.cli.evaluate import (
    FixtureResult,
    EXPECTED_FINDINGS_PATH,
    FIXTURES_DIR,
    build_report,
    load_expected_fixtures,
    report_to_dict,
    report_to_markdown,
)


def _result(fixture="f", expected=True, candidates=1, accepted=1):
    return FixtureResult(
        fixture=fixture, expected=expected, candidate_count=candidates,
        accepted_count=accepted, rejected_count=0, needs_review_count=0,
        static_corroborated_count=0, latency_seconds=0.5,
    )


def test_report_to_dict_has_required_top_level_keys():
    report = build_report([_result()])
    data = report_to_dict(report)

    for key in ("before_validation", "after_validation", "total_candidates", "total_accepted",
                "validation_acceptance_rate", "static_analysis_agreement_rate", "fixtures", "known_limitations"):
        assert key in data


def test_report_to_dict_matrix_has_metric_fields():
    report = build_report([_result()])
    data = report_to_dict(report)
    for key in ("tp", "fp", "fn", "tn", "precision", "recall", "f1", "false_positive_rate"):
        assert key in data["before_validation"]
        assert key in data["after_validation"]


def test_report_to_markdown_includes_fixture_rows_and_limitations():
    report = build_report([_result(fixture="sql_injection")])
    md = report_to_markdown(report)
    assert "sql_injection" in md
    assert "Before vs. after validation" in md
    assert "Known limitations" in md
    assert "spec §20" in md


def test_expected_fixtures_file_loads_and_files_exist():
    # Real fixture data, not synthetic -- catches a typo'd filename or
    # malformed JSONL line before a real evaluation run would.
    fixtures = load_expected_fixtures(EXPECTED_FINDINGS_PATH)
    assert len(fixtures) > 0
    for fixture in fixtures:
        assert (FIXTURES_DIR / fixture.file).exists(), f"missing fixture file: {fixture.file}"


def test_expected_fixtures_have_both_positive_and_negative_cases():
    fixtures = load_expected_fixtures(EXPECTED_FINDINGS_PATH)
    assert any(f.expected for f in fixtures)
    assert any(not f.expected for f in fixtures)

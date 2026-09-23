from driftwatch.review.models import CandidateFinding
from driftwatch.validation.evidence import validate_syntactic


def _chunk(**overrides):
    chunk = {
        "file": "app.py",
        "start_line": 10,
        "end_line": 20,
        "type": "function_definition",
        "diff_ranges": [(12, 14)],
    }
    chunk.update(overrides)
    return chunk


def _candidate(**overrides):
    fields = {
        "category": "security",
        "severity": "high",
        "file_path": "app.py",
        "start_line": 12,
        "end_line": 13,
        "title": "t",
        "description": "d",
        "reasoning_summary": "r",
        "confidence": 0.8,
    }
    fields.update(overrides)
    return CandidateFinding(**fields)


def test_rejects_wrong_file():
    result = validate_syntactic(_candidate(file_path="other.py"), _chunk())
    assert result.passed is False
    assert "does not match" in result.reasons[0]


def test_rejects_location_outside_chunk_bounds():
    result = validate_syntactic(_candidate(start_line=1, end_line=2), _chunk())
    assert result.passed is False
    assert "outside" in result.reasons[0]


def test_rejects_inverted_range():
    result = validate_syntactic(_candidate(start_line=15, end_line=12), _chunk())
    assert result.passed is False


def test_accepts_location_within_chunk_and_overlapping_diff():
    result = validate_syntactic(_candidate(), _chunk())
    assert result.passed is True
    assert result.diff_overlap is True
    assert any(e.source == "ast" for e in result.evidence)
    assert any(e.source == "diff" for e in result.evidence)


def test_passes_but_flags_no_diff_overlap():
    # location within chunk, but outside the actual changed lines
    result = validate_syntactic(_candidate(start_line=18, end_line=19), _chunk())
    assert result.passed is True
    assert result.diff_overlap is False
    assert any("does not overlap" in r for r in result.reasons)


def test_missing_diff_ranges_is_neutral_not_a_false_overlap_claim():
    # if diff_ranges is empty (e.g. not populated), don't claim overlap
    # happened, and don't penalize either -- just skip the check.
    result = validate_syntactic(_candidate(), _chunk(diff_ranges=[]))
    assert result.passed is True
    assert result.diff_overlap is False
    assert any("unavailable" in r for r in result.reasons)
    assert not any(e.source == "diff" and "overlaps a changed line" in e.description for e in result.evidence)

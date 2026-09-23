from driftwatch.review.models import Finding
from driftwatch.validation.deduplication import deduplicate


def _finding(**overrides) -> Finding:
    fields = dict(
        id="id",
        category="security",
        severity="high",
        title="t",
        description="d",
        repository="o/r",
        pull_request=1,
        file_path="app.py",
        start_line=10,
        end_line=12,
        changed_code="code",
        validation_score=0.5,
    )
    fields.update(overrides)
    return Finding(**fields)


def test_overlapping_findings_in_same_file_and_category_are_collapsed():
    a = _finding(id="a", start_line=10, end_line=12, validation_score=0.6)
    b = _finding(id="b", start_line=11, end_line=13, validation_score=0.9)
    result = deduplicate([(a, {}), (b, {})])
    assert len(result) == 1
    assert result[0][0].id == "b"  # higher score wins


def test_non_overlapping_findings_are_kept_separate():
    a = _finding(id="a", start_line=10, end_line=12)
    b = _finding(id="b", start_line=50, end_line=52)
    result = deduplicate([(a, {}), (b, {})])
    assert {r[0].id for r in result} == {"a", "b"}


def test_different_category_not_deduplicated_even_if_overlapping():
    a = _finding(id="a", category="security", start_line=10, end_line=12)
    b = _finding(id="b", category="bug", start_line=10, end_line=12)
    result = deduplicate([(a, {}), (b, {})])
    assert {r[0].id for r in result} == {"a", "b"}


def test_different_file_not_deduplicated_even_if_lines_overlap():
    a = _finding(id="a", file_path="app.py", start_line=10, end_line=12)
    b = _finding(id="b", file_path="other.py", start_line=10, end_line=12)
    result = deduplicate([(a, {}), (b, {})])
    assert {r[0].id for r in result} == {"a", "b"}

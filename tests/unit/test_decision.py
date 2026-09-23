from driftwatch.review import decision
from driftwatch.review.models import CandidateFinding
from driftwatch.validation.scoring import ValidationResult


def _candidate(**overrides) -> CandidateFinding:
    fields = dict(
        category="security",
        severity="high",
        file_path="app.py",
        start_line=1,
        end_line=2,
        title="Finding",
        description="desc",
        reasoning_summary="reason",
        confidence=0.9,
    )
    fields.update(overrides)
    return CandidateFinding(**fields)


def test_decide_populates_finding_from_validation_result(monkeypatch):
    fake_result = ValidationResult(status="accepted", score=0.91, reasons=["r1"], evidence=[])
    monkeypatch.setattr(decision, "validate", lambda candidate, chunk: fake_result)

    chunk = {"text": "subprocess.run(x, shell=True)"}
    decided = decision.decide([(_candidate(), chunk)], "owner/repo", 1)

    assert len(decided) == 1
    finding, returned_chunk = decided[0]
    assert finding.validation_status == "accepted"
    assert finding.validation_score == 0.91
    assert finding.changed_code == "subprocess.run(x, shell=True)"
    assert returned_chunk is chunk


def test_decide_passes_through_rejected_and_needs_review(monkeypatch):
    results = iter([
        ValidationResult(status="rejected", score=0.1, reasons=[], evidence=[]),
        ValidationResult(status="needs_review", score=0.6, reasons=[], evidence=[]),
    ])
    monkeypatch.setattr(decision, "validate", lambda candidate, chunk: next(results))

    chunk_a = {"text": "a", "start_line": 1, "end_line": 1, "file": "a.py"}
    chunk_b = {"text": "b", "start_line": 10, "end_line": 10, "file": "b.py"}
    decided = decision.decide(
        [(_candidate(file_path="a.py"), chunk_a), (_candidate(file_path="b.py"), chunk_b)],
        "owner/repo",
        1,
    )

    statuses = {f.validation_status for f, _ in decided}
    assert statuses == {"rejected", "needs_review"}

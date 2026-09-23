from driftwatch.review import decision
from driftwatch.review.models import CandidateFinding


def _candidate(confidence: float, title: str = "Finding") -> CandidateFinding:
    return CandidateFinding(
        category="security",
        severity="high",
        file_path="app.py",
        start_line=1,
        end_line=2,
        title=title,
        description="desc",
        reasoning_summary="reason",
        confidence=confidence,
    )


def test_low_confidence_findings_are_dropped(monkeypatch):
    monkeypatch.setattr(decision.config, "SECURITY_MIN_CONFIDENCE", 0.6)
    chunk = {"text": "code"}
    assert decision.decide([(_candidate(0.3), chunk)], "owner/repo", 1) == []


def test_high_confidence_findings_marked_needs_review(monkeypatch):
    monkeypatch.setattr(decision.config, "SECURITY_MIN_CONFIDENCE", 0.6)
    chunk = {"text": "subprocess.run(x, shell=True)"}
    decided = decision.decide([(_candidate(0.9), chunk)], "owner/repo", 1)
    assert len(decided) == 1
    finding, returned_chunk = decided[0]
    assert finding.validation_status == "needs_review"
    assert finding.changed_code == "subprocess.run(x, shell=True)"
    assert returned_chunk is chunk

from driftwatch.review.models import CandidateFinding, Finding


def test_candidate_finding_requires_core_fields():
    finding = CandidateFinding(
        category="security",
        severity="high",
        file_path="app.py",
        start_line=10,
        end_line=12,
        title="Unsafe shell execution",
        description="User input reaches a shell command.",
        reasoning_summary="subprocess.run called with shell=True and unsanitized input.",
        confidence=0.8,
    )
    assert finding.suggested_fix is None


def test_finding_defaults_to_needs_review():
    finding = Finding(
        id="abc123",
        category="security",
        severity="high",
        title="Unsafe shell execution",
        description="desc",
        repository="owner/repo",
        pull_request=1,
        file_path="app.py",
        start_line=10,
        end_line=12,
        changed_code="subprocess.run(x, shell=True)",
    )
    assert finding.validation_status == "needs_review"
    assert finding.evidence == []
    assert finding.static_matches == []

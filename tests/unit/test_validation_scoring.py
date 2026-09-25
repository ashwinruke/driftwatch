from driftwatch.review.models import CandidateFinding
from driftwatch.validation.scoring import compute_score, decide_status
from driftwatch.validation.validator import validate_security


def test_llm_confidence_alone_cannot_reach_accept_threshold(monkeypatch):
    import driftwatch.validation.scoring as scoring
    monkeypatch.setattr(scoring.config, "VALIDATION_ACCEPT_THRESHOLD", 0.75)

    # Maximum possible confidence, zero of every other evidence signal.
    score = compute_score(diff_evidence=0.0, static_corroboration=0.0, ast_consistency=0.0, llm_confidence=1.0)
    assert score < 0.75
    assert score == 0.15  # exactly the LLM-confidence weight


def test_full_corroboration_is_accepted(monkeypatch):
    import driftwatch.validation.scoring as scoring
    monkeypatch.setattr(scoring.config, "VALIDATION_ACCEPT_THRESHOLD", 0.75)
    monkeypatch.setattr(scoring.config, "VALIDATION_REVIEW_THRESHOLD", 0.50)

    score = compute_score(diff_evidence=1.0, static_corroboration=1.0, ast_consistency=1.0, llm_confidence=0.8)
    assert decide_status(score) == "accepted"


def test_partial_evidence_lands_in_needs_review(monkeypatch):
    import driftwatch.validation.scoring as scoring
    monkeypatch.setattr(scoring.config, "VALIDATION_ACCEPT_THRESHOLD", 0.75)
    monkeypatch.setattr(scoring.config, "VALIDATION_REVIEW_THRESHOLD", 0.50)

    # diff+ast evidence but no static corroboration, moderate confidence
    score = compute_score(diff_evidence=1.0, static_corroboration=0.0, ast_consistency=1.0, llm_confidence=0.5)
    assert decide_status(score) == "needs_review"


def test_weak_evidence_is_rejected(monkeypatch):
    import driftwatch.validation.scoring as scoring
    monkeypatch.setattr(scoring.config, "VALIDATION_ACCEPT_THRESHOLD", 0.75)
    monkeypatch.setattr(scoring.config, "VALIDATION_REVIEW_THRESHOLD", 0.50)

    score = compute_score(diff_evidence=0.6, static_corroboration=0.0, ast_consistency=1.0, llm_confidence=0.2)
    assert decide_status(score) == "rejected"


def test_security_result_carries_the_component_scores_that_produced_it():
    chunk = {
        "file": "app.py",
        "start_line": 10,
        "end_line": 20,
        "type": "function_definition",
        "diff_ranges": [(12, 14)],
        "static_matches": [],
    }
    candidate = CandidateFinding(
        category="security", severity="high", file_path="app.py",
        start_line=12, end_line=13, title="t", description="d",
        reasoning_summary="r", confidence=0.8,
    )
    result = validate_security(candidate, chunk)
    assert result.components is not None
    # diff_overlap is True (12-13 overlaps the 12-14 diff range) -> 1.0;
    # no static_matches -> 0.0; AST containment is always 1.0 once syntactic
    # validation passes; llm_confidence is the candidate's own confidence.
    assert result.components.diff_evidence == 1.0
    assert result.components.static_corroboration == 0.0
    assert result.components.ast_consistency == 1.0
    assert result.components.llm_confidence == 0.8

from typing import Literal

from pydantic import BaseModel

from driftwatch.app import config
from driftwatch.review.models import Evidence

# Spec §17's initial weighting -- engineering defaults, not scientifically
# proven constants, but fixed here (not per-request configurable) since
# they're a property of the scoring formula itself, not deployment config.
WEIGHT_DIFF_EVIDENCE = 0.35
WEIGHT_STATIC_CORROBORATION = 0.30
WEIGHT_AST_CONSISTENCY = 0.20
WEIGHT_LLM_CONFIDENCE = 0.15


class ValidationComponents(BaseModel):
    """The four inputs that produced a ValidationResult.score, kept
    alongside it (not just the combined number) so the dashboard's finding
    detail page (spec §53) can show the real breakdown rather than
    re-deriving or guessing it after the fact."""

    diff_evidence: float
    static_corroboration: float
    ast_consistency: float
    llm_confidence: float


class ValidationResult(BaseModel):
    status: Literal["accepted", "rejected", "needs_review"]
    score: float
    reasons: list[str] = []
    evidence: list[Evidence] = []
    components: ValidationComponents | None = None


def compute_score(diff_evidence: float, static_corroboration: float, ast_consistency: float, llm_confidence: float) -> float:
    """LLM confidence is capped at 15% of the total, so it can never alone
    reach VALIDATION_ACCEPT_THRESHOLD (0.75 default): confidence=1.0 with
    zero other evidence contributes only 0.15 -- satisfies spec §17's "do
    not allow LLM confidence alone to exceed the acceptance threshold" by
    construction, not by a separate check."""
    return (
        WEIGHT_DIFF_EVIDENCE * diff_evidence
        + WEIGHT_STATIC_CORROBORATION * static_corroboration
        + WEIGHT_AST_CONSISTENCY * ast_consistency
        + WEIGHT_LLM_CONFIDENCE * llm_confidence
    )


def decide_status(score: float) -> Literal["accepted", "rejected", "needs_review"]:
    if score >= config.VALIDATION_ACCEPT_THRESHOLD:
        return "accepted"
    if score >= config.VALIDATION_REVIEW_THRESHOLD:
        return "needs_review"
    return "rejected"

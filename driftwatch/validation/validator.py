import logging

from driftwatch.review.models import CandidateFinding, Evidence, StaticMatch
from driftwatch.validation.evidence import validate_syntactic
from driftwatch.validation.rules import check_claim_consistency
from driftwatch.validation.scoring import ValidationResult, compute_score, decide_status

logger = logging.getLogger("driftwatch")

# Small tolerance between a static-analysis match's line and the finding's
# reported range, to absorb minor line-mapping slop rather than requiring
# an exact match.
_LINE_SLOP = 2


def _corroborating_matches(candidate: CandidateFinding, static_matches: list[StaticMatch]) -> list[StaticMatch]:
    return [
        m for m in static_matches
        if m.line is not None
        and (candidate.start_line - _LINE_SLOP) <= m.line <= (candidate.end_line + _LINE_SLOP)
    ]


def validate(candidate: CandidateFinding, chunk: dict) -> ValidationResult:
    """The validation layer: a candidate finding is trustworthy enough to
    post only if this returns "accepted". Never treats LLM confidence
    alone as sufficient -- see scoring.compute_score."""
    syntactic = validate_syntactic(candidate, chunk)
    if not syntactic.passed:
        return ValidationResult(status="rejected", score=0.0, reasons=syntactic.reasons, evidence=syntactic.evidence)

    static_matches = chunk.get("static_matches", [])
    corroborating = _corroborating_matches(candidate, static_matches)

    reasons = list(syntactic.reasons)
    evidence = list(syntactic.evidence)
    for match in corroborating:
        evidence.append(Evidence(
            source=match.tool,
            description=match.message,
            file_path=match.file_path,
            start_line=match.line,
            rule_id=match.rule_id,
        ))

    if corroborating:
        tools = ", ".join(sorted({m.tool for m in corroborating}))
        reasons.append(f"Corroborated by {len(corroborating)} static-analysis finding(s) ({tools})")
    else:
        # No matching tool finding does NOT mean the LLM finding is false --
        # it just means confidence should be lower absent other evidence.
        reasons.append("No static-analysis corroboration found")

    consistent, claim_reason = check_claim_consistency(candidate.description, candidate.reasoning_summary)
    if claim_reason:
        reasons.append(claim_reason)

    score = compute_score(
        diff_evidence=1.0 if syntactic.diff_overlap else 0.6,
        static_corroboration=1.0 if corroborating else 0.0,
        ast_consistency=1.0,
        llm_confidence=candidate.confidence,
    )
    if not consistent:
        score *= 0.7

    status = decide_status(score)
    logger.info(f"Validated '{candidate.title}': {status} (score={round(score, 3)})")
    return ValidationResult(status=status, score=round(score, 3), reasons=reasons, evidence=evidence)

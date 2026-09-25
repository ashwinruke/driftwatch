import logging

from driftwatch.review.models import CandidateFinding, Evidence, StaticMatch
from driftwatch.validation.evidence import validate_syntactic
from driftwatch.validation.rules import check_claim_consistency
from driftwatch.validation.scoring import ValidationComponents, ValidationResult, compute_score, decide_status

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


def validate_security(candidate: CandidateFinding, chunk: dict) -> ValidationResult:
    """Stages A-E for a code finding: location/diff/AST checks, static-
    analysis corroboration, claim-consistency wording, then a weighted
    score. Never treats LLM confidence alone as sufficient -- see
    scoring.compute_score."""
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

    diff_evidence = 1.0 if syntactic.diff_overlap else 0.6
    static_corroboration = 1.0 if corroborating else 0.0
    ast_consistency = 1.0
    score = compute_score(
        diff_evidence=diff_evidence,
        static_corroboration=static_corroboration,
        ast_consistency=ast_consistency,
        llm_confidence=candidate.confidence,
    )
    if not consistent:
        score *= 0.7

    status = decide_status(score)
    logger.info(f"Validated '{candidate.title}': {status} (score={round(score, 3)})")
    components = ValidationComponents(
        diff_evidence=diff_evidence,
        static_corroboration=static_corroboration,
        ast_consistency=ast_consistency,
        llm_confidence=candidate.confidence,
    )
    return ValidationResult(status=status, score=round(score, 3), reasons=reasons, evidence=evidence, components=components)


def validate_documentation(candidate: CandidateFinding, chunk: dict) -> ValidationResult:
    """Per spec §18: "Use the existing DriftWatch matching + verification
    workflow, then pass the result through the common validation/reporting
    pipeline." A documentation candidate only exists because it already
    cleared doc-drift's own two-stage check (embedding similarity >=
    threshold in matcher.py, then an LLM verdict of OUTDATED in
    drafter.py) -- that already *is* the evidence-gathering for this
    category. The code-specific checks in validate_security (location
    within a code chunk, diff-line overlap, static-analysis corroboration)
    don't apply: a documentation finding is about a doc file, not a line
    of the diff, so this is a pass-through, not a weaker check."""
    evidence = [
        Evidence(
            source="diff",
            description=(
                f"Changed {chunk['type']} '{chunk.get('name', chunk['file'])}' in {chunk['file']} "
                f"matched this doc section by embedding similarity >= threshold"
            ),
            file_path=chunk["file"],
            start_line=chunk["start_line"],
            end_line=chunk["end_line"],
        ),
        Evidence(
            source="llm",
            description=candidate.reasoning_summary,
            file_path=candidate.file_path,
        ),
    ]
    score = round(candidate.confidence, 3)
    logger.info(f"Validated '{candidate.title}' (documentation): accepted (score={score})")
    return ValidationResult(
        status="accepted",
        score=score,
        reasons=["Verified outdated by the existing doc-drift matching + LLM verification workflow"],
        evidence=evidence,
    )


def validate(candidate: CandidateFinding, chunk: dict) -> ValidationResult:
    """The validation layer: a candidate finding is trustworthy enough to
    post only if this returns "accepted". Dispatches per spec §18, which
    gives each category its own policy rather than one universal check."""
    if candidate.category == "documentation":
        return validate_documentation(candidate, chunk)
    return validate_security(candidate, chunk)

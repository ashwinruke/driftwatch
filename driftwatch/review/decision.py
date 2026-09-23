import logging
import uuid

from driftwatch.app import config
from driftwatch.review.models import CandidateFinding, Finding

logger = logging.getLogger("driftwatch")


def decide(
    candidates: list[tuple[CandidateFinding, dict]],
    repository: str,
    pull_request: int,
) -> list[tuple[Finding, dict]]:
    """Phase 1: no validation layer yet, just a confidence floor. Every
    finding that clears the bar is explicitly marked needs_review, not
    accepted -- nothing has independently checked it. Phase 2 replaces this
    function's internals with real evidence-based validation; the
    (candidates, repository, pull_request) -> decided contract stays the
    same, so the orchestrator won't need to change."""
    decided = []
    for candidate, chunk in candidates:
        if candidate.confidence < config.SECURITY_MIN_CONFIDENCE:
            logger.info(f"Dropping low-confidence finding '{candidate.title}' (confidence={candidate.confidence})")
            continue

        finding = Finding(
            id=str(uuid.uuid4()),
            category=candidate.category,
            severity=candidate.severity,
            title=candidate.title,
            description=candidate.description,
            repository=repository,
            pull_request=pull_request,
            file_path=candidate.file_path,
            start_line=candidate.start_line,
            end_line=candidate.end_line,
            changed_code=chunk["text"],
            llm_confidence=candidate.confidence,
            validation_status="needs_review",
            suggested_fix=candidate.suggested_fix,
        )
        decided.append((finding, chunk))
    return decided

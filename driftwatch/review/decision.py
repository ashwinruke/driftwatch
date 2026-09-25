import logging
import uuid

from driftwatch.review.models import CandidateFinding, Finding
from driftwatch.validation.deduplication import deduplicate
from driftwatch.validation.validator import validate

logger = logging.getLogger("driftwatch")


def decide(
    candidates: list[tuple[CandidateFinding, dict]],
    repository: str,
    pull_request: int,
) -> list[tuple[Finding, dict]]:
    """Phase 2: every candidate is run through the real validation pipeline
    (driftwatch.validation) instead of Phase 1's bare confidence floor.
    Same (candidates, repository, pull_request) -> decided contract as
    before, so the orchestrator didn't need to change its call site."""
    decided = []
    for candidate, chunk in candidates:
        result = validate(candidate, chunk)

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
            evidence=result.evidence,
            llm_confidence=candidate.confidence,
            validation_score=result.score,
            static_matches=list(chunk.get("static_matches", [])),
            validation_status=result.status,
            validation_reasons=result.reasons,
            validation_components=result.components.model_dump() if result.components else None,
            suggested_fix=candidate.suggested_fix,
        )
        decided.append((finding, chunk))

    return deduplicate(decided)

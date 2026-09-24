"""Adapts the existing doc-drift matching + verification pipeline
(matcher.find_stale_sections, drafter.draft_update -- both unchanged) into
the shared CandidateFinding schema, per spec §18's documentation policy:
"Use the existing DriftWatch matching + verification workflow, then pass
the result through the common validation/reporting pipeline." This module
is that adaptation layer; it doesn't change how staleness is detected."""

import logging

from driftwatch.analyzers.documentation.drafter import draft_update
from driftwatch.analyzers.documentation.matcher import find_stale_sections
from driftwatch.retry import with_retry
from driftwatch.review.models import CandidateFinding

logger = logging.getLogger("driftwatch")

name = "documentation"


def analyze_chunk(chunk: dict, repository: str) -> list[tuple[CandidateFinding, dict]]:
    """For one changed code chunk, find doc sections it may have made
    stale, verify each with the LLM, and return a CandidateFinding for
    every section confirmed OUTDATED (paired with the code chunk that
    triggered it, matching the (CandidateFinding, dict) shape
    decision.decide() expects from every engine).

    Finding.file_path/start_line/end_line describe the code chunk in
    every other category; for documentation there's no code location to
    report -- the issue is in the doc file, not the diff. file_path is
    set to the doc file instead (start_line/end_line stay 1/1: doc_sections
    doesn't track real line numbers -- a known limitation, not a fabricated
    one). validation/validator.py's validate_documentation() recognizes
    category="documentation" and doesn't try to check these against the
    code chunk's bounds the way it does for security findings."""
    stale_sections = find_stale_sections(repository, chunk)
    results = []

    for section in stale_sections:
        logger.info(f"  -> Checking drift for '{section['heading']}' ({section['file_path']}) score={section['similarity']}")
        result = with_retry(draft_update, chunk, section)
        logger.info(f"     Verdict: {result['verdict']} | {result['reason']}")
        if result["verdict"] != "OUTDATED":
            continue

        candidate = CandidateFinding(
            category="documentation",
            severity="info",
            file_path=section["file_path"],
            start_line=1,
            end_line=1,
            title=section["heading"] or section["file_path"],
            description=result["reason"],
            reasoning_summary=result["reason"],
            suggested_fix=result["draft"] or None,
            confidence=section["similarity"],
        )
        results.append((candidate, chunk))

    return results

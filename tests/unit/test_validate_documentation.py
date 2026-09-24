from driftwatch.review.models import CandidateFinding
from driftwatch.validation.validator import validate, validate_documentation


def _candidate(**overrides) -> CandidateFinding:
    fields = dict(
        category="documentation",
        severity="info",
        file_path="README.md",
        start_line=1,
        end_line=1,
        title="Usage",
        description="run_query now requires a user_id parameter.",
        reasoning_summary="run_query now requires a user_id parameter.",
        suggested_fix="Call run_query(user_id).",
        confidence=0.83,
    )
    fields.update(overrides)
    return CandidateFinding(**fields)


def _chunk(**overrides):
    chunk = {"file": "app.py", "type": "function_definition", "name": "run_query", "start_line": 10, "end_line": 12}
    chunk.update(overrides)
    return chunk


def test_documentation_candidate_is_always_accepted():
    result = validate_documentation(_candidate(), _chunk())
    assert result.status == "accepted"


def test_score_equals_the_embedding_similarity_confidence():
    result = validate_documentation(_candidate(confidence=0.91), _chunk())
    assert result.score == 0.91


def test_evidence_includes_diff_and_llm_sources():
    result = validate_documentation(_candidate(), _chunk())
    sources = {e.source for e in result.evidence}
    assert "diff" in sources
    assert "llm" in sources


def test_dispatcher_routes_documentation_category_to_validate_documentation():
    # A location that would fail validate_security's Stage A (file_path
    # doesn't match the chunk's file) must NOT cause a rejection here --
    # confirms validate() actually dispatches instead of always running
    # the code-specific checks.
    result = validate(_candidate(file_path="README.md"), _chunk(file="app.py"))
    assert result.status == "accepted"

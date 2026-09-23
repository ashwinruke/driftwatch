from typing import Literal

from pydantic import BaseModel


class Evidence(BaseModel):
    source: Literal["diff", "ast", "semgrep", "bandit", "gitleaks", "llm"]
    description: str
    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    rule_id: str | None = None


class StaticMatch(BaseModel):
    tool: str
    rule_id: str
    file_path: str
    line: int | None = None
    message: str


class CandidateFinding(BaseModel):
    """Raw LLM output, pre-decision. Matches the structured-output schema
    the LLM provider is asked to return (spec §32)."""

    category: Literal["security", "bug", "quality", "documentation"]
    severity: Literal["critical", "high", "medium", "low", "info"]
    file_path: str
    start_line: int
    end_line: int
    title: str
    description: str
    reasoning_summary: str
    suggested_fix: str | None = None
    confidence: float


class Finding(BaseModel):
    """Post-decision finding (spec §9). validation_score/static_matches stay
    empty and validation_status stays "needs_review" until Phase 2's
    validation layer exists to actually populate them."""

    id: str
    category: Literal["security", "bug", "quality", "documentation"]
    severity: Literal["critical", "high", "medium", "low", "info"]

    title: str
    description: str

    repository: str
    pull_request: int

    file_path: str
    start_line: int
    end_line: int

    changed_code: str
    evidence: list[Evidence] = []

    llm_confidence: float | None = None
    validation_score: float | None = None

    static_matches: list[StaticMatch] = []
    validation_status: Literal["accepted", "rejected", "needs_review"] = "needs_review"

    suggested_fix: str | None = None

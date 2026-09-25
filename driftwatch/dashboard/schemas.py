"""Pydantic response models for the dashboard read API (spec §59: "Use
Pydantic response models. Do not expose internal database models
directly.") -- these are deliberately separate from review/models.py's
Finding/Evidence, which describe an in-flight review, not a dashboard
read."""

from datetime import datetime

from pydantic import BaseModel


class RepositorySummary(BaseModel):
    id: int
    full_name: str
    default_branch: str | None
    review_count: int
    findings_count: int
    validation_acceptance_rate: float | None
    last_review: datetime | None


class ReviewRunSummary(BaseModel):
    id: int
    pr_number: int
    pr_title: str | None
    pr_author: str | None
    run_type: str
    status: str
    started_at: datetime
    completed_at: datetime | None


class RepositoryDetail(BaseModel):
    id: int
    full_name: str
    default_branch: str | None
    total_reviews: int
    total_findings: int
    last_review: datetime | None
    recent_reviews: list[ReviewRunSummary]


class FindingSummary(BaseModel):
    id: str
    category: str
    severity: str
    file_path: str
    start_line: int
    end_line: int
    title: str
    validation_status: str
    validation_score: float | None
    static_corroborated: bool


class ReviewStats(BaseModel):
    files_analyzed: int
    candidate_findings: int
    accepted: int
    rejected: int
    needs_review: int
    comments_posted: int


class ReviewDetail(BaseModel):
    id: int
    repository_id: int
    repository_full_name: str
    pr_number: int
    pr_title: str | None
    pr_author: str | None
    head_sha: str | None
    run_type: str
    status: str
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
    stats: ReviewStats
    findings: list[FindingSummary]


class EvidenceItem(BaseModel):
    source: str
    description: str
    file_path: str | None
    start_line: int | None
    end_line: int | None
    rule_id: str | None


class ValidationBreakdown(BaseModel):
    diff_evidence: float | None
    static_corroboration: float | None
    ast_consistency: float | None
    llm_confidence: float | None
    final_score: float


class CommentRef(BaseModel):
    comment_type: str
    github_comment_id: int | None
    github_url: str | None
    posted_at: datetime


class FindingDetail(BaseModel):
    id: str
    review_run_id: int
    repository_id: int
    category: str
    severity: str
    file_path: str
    start_line: int
    end_line: int
    title: str
    description: str
    suggested_fix: str | None
    validation_status: str
    validation_score: float | None
    llm_confidence: float | None
    validation_reasons: list[str]
    evidence: list[EvidenceItem]
    # None for documentation findings -- validate_documentation() is a
    # pass-through with no four-signal breakdown to show (see
    # validation/validator.py).
    validation_breakdown: ValidationBreakdown | None
    comment: CommentRef | None


class OverviewResponse(BaseModel):
    total_repositories: int
    total_review_runs: int
    total_prs_reviewed: int
    total_findings: int
    accepted_findings: int
    rejected_findings: int
    needs_review_findings: int
    validation_acceptance_rate: float | None
    average_review_latency_seconds: float | None
    findings_by_category: dict[str, int]
    findings_by_severity: dict[str, int]

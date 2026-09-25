"""Dashboard read API (spec §59, golden-path subset -- /metrics,
/observability, /evaluation/* are a follow-up, see docs/roadmap.md's
Phase 6 report). Every route builds a schemas.py Pydantic model from
queries.py's raw rows; nothing here returns a database row directly."""

from fastapi import APIRouter, HTTPException

from driftwatch.dashboard import queries, schemas

router = APIRouter(prefix="/api/v1")


@router.get("/dashboard/overview", response_model=schemas.OverviewResponse)
def get_overview():
    return schemas.OverviewResponse(**queries.get_overview())


@router.get("/repositories", response_model=list[schemas.RepositorySummary])
def list_repositories():
    return [
        schemas.RepositorySummary(
            id=row["id"],
            full_name=row["full_name"],
            default_branch=row["default_branch"],
            review_count=row["review_count"],
            findings_count=row["findings_count"],
            validation_acceptance_rate=row["validation_acceptance_rate"],
            last_review=row["last_review"],
        )
        for row in queries.list_repositories()
    ]


@router.get("/repositories/{repository_id}", response_model=schemas.RepositoryDetail)
def get_repository_detail(repository_id: int):
    row = queries.get_repository_detail(repository_id)
    if not row:
        raise HTTPException(status_code=404, detail="Repository not found")
    return schemas.RepositoryDetail(
        id=row["id"],
        full_name=row["full_name"],
        default_branch=row["default_branch"],
        total_reviews=row["total_reviews"],
        total_findings=row["total_findings"],
        last_review=row["last_review"],
        recent_reviews=[schemas.ReviewRunSummary(**r) for r in row["recent_reviews"]],
    )


@router.get("/repositories/{repository_id}/reviews", response_model=list[schemas.ReviewRunSummary])
def list_repository_reviews(repository_id: int, limit: int = 20, offset: int = 0):
    return [schemas.ReviewRunSummary(**row) for row in queries.list_repository_reviews(repository_id, limit, offset)]


@router.get("/reviews/{review_run_id}", response_model=schemas.ReviewDetail)
def get_review_detail(review_run_id: int):
    row = queries.get_review_detail(review_run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Review not found")
    return schemas.ReviewDetail(
        id=row["id"],
        repository_id=row["repository_id"],
        repository_full_name=row["repository_full_name"],
        pr_number=row["pr_number"],
        pr_title=row["pr_title"],
        pr_author=row["pr_author"],
        head_sha=row["head_sha"],
        run_type=row["run_type"],
        status=row["status"],
        error_message=row["error_message"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        stats=schemas.ReviewStats(
            files_analyzed=row["files_analyzed"],
            candidate_findings=row["candidate_findings"],
            accepted=row["accepted"],
            rejected=row["rejected"],
            needs_review=row["needs_review"],
            comments_posted=row["comments_posted"],
        ),
        findings=[schemas.FindingSummary(**f) for f in row["findings"]],
    )


@router.get("/findings/{finding_id}", response_model=schemas.FindingDetail)
def get_finding_detail(finding_id: str):
    row = queries.get_finding_detail(finding_id)
    if not row:
        raise HTTPException(status_code=404, detail="Finding not found")

    vr = row["validation_result"] or {}
    component_keys = ("diff_evidence_score", "static_corroboration_score", "ast_consistency_score", "llm_confidence_score")
    has_breakdown = any(vr.get(k) is not None for k in component_keys)
    breakdown = (
        schemas.ValidationBreakdown(
            diff_evidence=vr.get("diff_evidence_score"),
            static_corroboration=vr.get("static_corroboration_score"),
            ast_consistency=vr.get("ast_consistency_score"),
            llm_confidence=vr.get("llm_confidence_score"),
            final_score=vr.get("final_score", row["validation_score"]),
        )
        if has_breakdown
        else None
    )

    return schemas.FindingDetail(
        id=row["id"],
        review_run_id=row["review_run_id"],
        category=row["category"],
        severity=row["severity"],
        file_path=row["file_path"],
        start_line=row["start_line"],
        end_line=row["end_line"],
        title=row["title"],
        description=row["description"],
        suggested_fix=row["suggested_fix"],
        validation_status=row["validation_status"],
        validation_score=row["validation_score"],
        llm_confidence=row["llm_confidence"],
        validation_reasons=row["validation_reasons"] or [],
        evidence=[schemas.EvidenceItem(**e) for e in row["evidence"]],
        validation_breakdown=breakdown,
        comment=schemas.CommentRef(**row["comment"]) if row["comment"] else None,
    )

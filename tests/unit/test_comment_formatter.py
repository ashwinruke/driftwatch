from driftwatch.reporting.comment_formatter import format_finding_comment
from driftwatch.reporting.pr_summary import format_pr_summary
from driftwatch.review.models import Finding


def _finding() -> Finding:
    return Finding(
        id="abc",
        category="security",
        severity="high",
        title="Unsafe shell execution",
        description="User input reaches shell=True.",
        repository="owner/repo",
        pull_request=1,
        file_path="app.py",
        start_line=10,
        end_line=12,
        changed_code="subprocess.run(x, shell=True)",
        llm_confidence=0.9,
        suggested_fix="Avoid shell=True.",
    )


def test_finding_comment_includes_key_fields():
    body = format_finding_comment(_finding())
    assert "Unsafe shell execution" in body
    assert "Avoid shell=True." in body
    assert "needs_review" in body
    assert "0.9" in body


def test_pr_summary_counts_by_category():
    finding = _finding()
    summary = format_pr_summary(files_analyzed=3, candidates=[finding], posted=[finding])
    assert "Files analyzed: 3" in summary
    assert "Candidate findings: 1" in summary
    assert "Posted findings: 1" in summary
    assert "Security" in summary

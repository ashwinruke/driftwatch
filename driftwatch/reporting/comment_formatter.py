from driftwatch.review.models import Finding

CODE_FENCE = "```"

_SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "info": "⚪",
}


def format_finding_comment(finding: Finding) -> str:
    emoji = _SEVERITY_EMOJI.get(finding.severity, "")
    body = (
        f"### {emoji} {finding.category.title()}: {finding.title}\n\n"
        f"**Issue**\n\n{finding.description}\n\n"
    )

    if finding.suggested_fix:
        body += f"**Suggested fix**\n\n{finding.suggested_fix}\n\n"

    body += (
        f"**Validation**\n\n"
        f"Status: `{finding.validation_status}` — unvalidated (Phase 1, no independent "
        f"evidence checking yet; a validation layer is planned)  \n"
        f"LLM confidence: {finding.llm_confidence}\n\n"
        f"---\n"
        f"*Posted automatically by DriftWatch AI Code Reviewer. This is an AI-generated "
        f"suggestion, not verified evidence — please review before acting on it.*"
    )
    return body

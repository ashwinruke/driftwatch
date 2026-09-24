from driftwatch.review.models import Finding


def _same_underlying_issue(finding: Finding, other: Finding) -> bool:
    if finding.file_path != other.file_path or finding.category != other.category:
        return False

    if finding.category == "documentation":
        # Documentation findings share a placeholder start_line/end_line
        # (1/1 -- doc_sections doesn't track real line numbers), so line
        # overlap would incorrectly merge every stale section in the same
        # file. Dedupe by exact title (the doc heading) instead.
        return finding.title == other.title

    return finding.start_line <= other.end_line and finding.end_line >= other.start_line


def deduplicate(decided: list[tuple[Finding, dict]]) -> list[tuple[Finding, dict]]:
    """Spec §16.1 Stage F: collapse findings that are the same underlying
    issue, keeping the highest-scored one per group. One underlying issue
    should normally produce one comment. "Same issue" means overlapping
    line ranges within the same file+category for code findings, or an
    exact title match for documentation findings (see _same_underlying_issue)."""
    groups: list[list[tuple[Finding, dict]]] = []

    for item in decided:
        finding, _ = item
        for group in groups:
            if _same_underlying_issue(finding, group[0][0]):
                group.append(item)
                break
        else:
            groups.append([item])

    return [max(group, key=lambda pair: pair[0].validation_score or 0.0) for group in groups]

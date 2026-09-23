from driftwatch.review.models import Finding


def deduplicate(decided: list[tuple[Finding, dict]]) -> list[tuple[Finding, dict]]:
    """Spec §16.1 Stage F: collapse findings that are the same underlying
    issue -- same file, same category, overlapping line ranges -- keeping
    the highest-scored one per group. One underlying issue should normally
    produce one comment."""
    groups: list[list[tuple[Finding, dict]]] = []

    for item in decided:
        finding, _ = item
        for group in groups:
            group_finding = group[0][0]
            if (
                finding.file_path == group_finding.file_path
                and finding.category == group_finding.category
                and finding.start_line <= group_finding.end_line
                and finding.end_line >= group_finding.start_line
            ):
                group.append(item)
                break
        else:
            groups.append([item])

    return [max(group, key=lambda pair: pair[0].validation_score or 0.0) for group in groups]

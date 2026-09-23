from dataclasses import dataclass, field

from driftwatch.review.models import CandidateFinding, Evidence


@dataclass
class SyntacticValidation:
    passed: bool
    diff_overlap: bool
    evidence: list[Evidence] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def validate_syntactic(candidate: CandidateFinding, chunk: dict) -> SyntacticValidation:
    """Spec §16.1 Stages A (location), B (diff relevance), C (AST context)
    as one pass, since they share the same chunk/candidate inputs.
    `passed=False` means reject outright -- the location is untrustworthy
    enough that no score should be computed. Diff relevance is syntactic
    only (line-range overlap): no symbol/data-flow tracking, per spec's own
    caution against claiming data-flow proof from syntactic evidence."""
    reasons: list[str] = []
    evidence: list[Evidence] = []

    # Stage A: location validation. The LLM must not have hallucinated a
    # location outside the code it was actually shown.
    if candidate.file_path != chunk["file"]:
        return SyntacticValidation(
            passed=False,
            diff_overlap=False,
            reasons=[f"Reported file '{candidate.file_path}' does not match the analyzed file '{chunk['file']}'"],
        )

    if candidate.start_line > candidate.end_line:
        return SyntacticValidation(passed=False, diff_overlap=False, reasons=["start_line is after end_line"])

    if not (
        chunk["start_line"] <= candidate.start_line <= chunk["end_line"]
        and chunk["start_line"] <= candidate.end_line <= chunk["end_line"]
    ):
        return SyntacticValidation(
            passed=False,
            diff_overlap=False,
            reasons=[
                f"Reported lines {candidate.start_line}-{candidate.end_line} fall outside "
                f"the analyzed chunk ({chunk['start_line']}-{chunk['end_line']})"
            ],
        )

    reasons.append("Location falls within the analyzed chunk")
    evidence.append(Evidence(
        source="diff",
        description="Finding location falls within the code chunk that was actually analyzed",
        file_path=candidate.file_path,
        start_line=candidate.start_line,
        end_line=candidate.end_line,
    ))

    # Stage B: diff relevance (syntactic overlap with the diff, not proof
    # of data flow).
    diff_ranges = chunk.get("diff_ranges", [])
    diff_overlap = any(cs <= candidate.end_line and ce >= candidate.start_line for cs, ce in diff_ranges)
    if not diff_ranges:
        reasons.append("Diff ranges unavailable for this chunk, diff-relevance check skipped")
    elif diff_overlap:
        reasons.append("Finding overlaps a changed line (syntactic check)")
        evidence.append(Evidence(
            source="diff",
            description="Finding's line range overlaps a changed line from the PR diff",
            file_path=candidate.file_path,
            start_line=candidate.start_line,
            end_line=candidate.end_line,
        ))
    else:
        reasons.append("Finding does not overlap any actually-changed line (syntactic check only)")

    # Stage C: AST context. The chunk itself is tree-sitter-derived, so
    # containment (checked above) already establishes this; record it as
    # explicit evidence for the audit trail rather than leaving it implicit.
    evidence.append(Evidence(
        source="ast",
        description=f"Finding is located inside a tree-sitter-identified {chunk['type']} (lines {chunk['start_line']}-{chunk['end_line']})",
        file_path=chunk["file"],
        start_line=chunk["start_line"],
        end_line=chunk["end_line"],
    ))

    return SyntacticValidation(passed=True, diff_overlap=diff_overlap, evidence=evidence, reasons=reasons)

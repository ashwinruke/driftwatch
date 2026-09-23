import re

# Spec §16.1 Stage E: claims must not overstate certainty beyond what's
# established. This is a deterministic keyword heuristic, not a second LLM
# call -- it only ever downgrades a score, never rejects outright, since a
# real issue described with strong language is still a real issue.
_OVERSTATED_PATTERNS = [
    r"\bwill always\b",
    r"\bguaranteed\b",
    r"\b100%\b",
    r"\bdefinitely (results?|leads?|causes?)\b",
    r"\bcertainly (results?|leads?|causes?)\b",
    r"\bwithout (a )?doubt\b",
]

_OVERSTATED_RE = re.compile("|".join(_OVERSTATED_PATTERNS), re.IGNORECASE)


def check_claim_consistency(description: str, reasoning_summary: str) -> tuple[bool, str | None]:
    text = f"{description} {reasoning_summary}"
    match = _OVERSTATED_RE.search(text)
    if match:
        return False, f"Description uses absolute language ('{match.group(0)}') not fully supported by syntactic-only evidence"
    return True, None

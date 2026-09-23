import base64
import logging

from driftwatch.ast.parser import (
    changed_line_ranges,
    extract_imports,
    extract_module_level_chunks,
    extract_surrounding_lines,
    find_anchor_line,
    find_enclosing_chunks,
    find_uncovered_ranges,
)
from driftwatch.github.client import get

logger = logging.getLogger("driftwatch")


def get_pr_files(owner: str, repo: str, pr_number: int, token: str):
    return get(f"/repos/{owner}/{repo}/pulls/{pr_number}/files", token).json()


def get_blob_content(owner: str, repo: str, blob_sha: str, token: str) -> bytes:
    resp = get(f"/repos/{owner}/{repo}/git/blobs/{blob_sha}", token)
    return base64.b64decode(resp.json()["content"])


def extract_changed_chunks(owner: str, repo: str, pr_number: int, token: str, include_module_level: bool = False):
    """include_module_level=True additionally:
    - emits a pseudo-chunk for changed lines not covered by any
      function/class (e.g. a module-level hardcoded secret)
    - computes an anchor_line per chunk (the first actually-changed line
      within it, required for posting a line-anchored review comment)
    - attaches top-level imports and a few lines of surrounding context
    Doc-drift's call site doesn't pass this, so its behavior is unchanged."""
    files = get_pr_files(owner, repo, pr_number, token)
    results = []

    for f in files:
        path = f["filename"]
        if not path.endswith(".py") or f["status"] == "removed":
            continue

        patch = f.get("patch")
        if not patch:
            logger.info(f"Skipping {path}: no patch available (binary file or diff too large for GitHub to include)")
            continue

        ranges = changed_line_ranges(patch)
        if not ranges:
            continue

        source_bytes = get_blob_content(owner, repo, f["sha"], token)
        chunks = find_enclosing_chunks(source_bytes, ranges)

        if include_module_level:
            uncovered = find_uncovered_ranges(ranges, chunks)
            chunks = chunks + extract_module_level_chunks(source_bytes, uncovered)

        for chunk in chunks:
            chunk["file"] = path
            if include_module_level:
                chunk["anchor_line"] = find_anchor_line(chunk["start_line"], chunk["end_line"], ranges)
                chunk["imports"] = extract_imports(source_bytes)
                context_before, context_after = extract_surrounding_lines(source_bytes, chunk["start_line"], chunk["end_line"])
                chunk["context_before"] = context_before
                chunk["context_after"] = context_after
            results.append(chunk)

    return results

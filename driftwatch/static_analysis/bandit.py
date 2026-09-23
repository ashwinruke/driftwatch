import json
import logging
import subprocess
from pathlib import Path

from driftwatch.review.models import StaticMatch
from driftwatch.static_analysis.executables import resolve_executable

logger = logging.getLogger("driftwatch")

TIMEOUT_SECONDS = 30


def run(directory: str) -> dict[str, list[StaticMatch]]:
    """Run Bandit (fully offline, no bundled rules needed -- its checks are
    built in) against every file in `directory`, once. Returns matches
    grouped by filename, line numbers relative to each file. Never raises;
    see semgrep.run()'s docstring for why."""
    try:
        result = subprocess.run(
            [resolve_executable("bandit"), "-f", "json", "-r", directory],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning(f"bandit timed out after {TIMEOUT_SECONDS}s, skipping static corroboration for this run")
        return {}
    except FileNotFoundError:
        logger.warning("bandit executable not found, skipping static corroboration")
        return {}

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.warning(f"bandit produced non-JSON output (exit code {result.returncode}), skipping static corroboration")
        return {}

    matches_by_file: dict[str, list[StaticMatch]] = {}
    for item in data.get("results", []):
        filename = Path(item["filename"]).name
        match = StaticMatch(
            tool="bandit",
            rule_id=item["test_id"],
            file_path=filename,
            line=item["line_number"],
            message=item["issue_text"],
        )
        matches_by_file.setdefault(filename, []).append(match)

    return matches_by_file

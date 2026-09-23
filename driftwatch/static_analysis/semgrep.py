import json
import logging
import subprocess
from pathlib import Path

from driftwatch.review.models import StaticMatch
from driftwatch.static_analysis.executables import resolve_executable

logger = logging.getLogger("driftwatch")

RULES_PATH = Path(__file__).parent / "rules" / "security.yml"
TIMEOUT_SECONDS = 30


def run(directory: str) -> dict[str, list[StaticMatch]]:
    """Run the bundled offline ruleset (RULES_PATH -- no network access,
    deliberately not --config auto) against every file in `directory`,
    once. Returns matches grouped by filename, with line numbers relative
    to each file as scanned -- the caller remaps to real file line numbers.
    Never raises: a failed/missing/timed-out tool just yields no
    corroboration for this run, per spec §31's static-tool-failure
    handling requirement."""
    try:
        result = subprocess.run(
            [resolve_executable("semgrep"), "--config", str(RULES_PATH), "--json", "--quiet", directory],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning(f"semgrep timed out after {TIMEOUT_SECONDS}s, skipping static corroboration for this run")
        return {}
    except FileNotFoundError:
        logger.warning("semgrep executable not found, skipping static corroboration")
        return {}

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.warning(f"semgrep produced non-JSON output (exit code {result.returncode}), skipping static corroboration")
        return {}

    matches_by_file: dict[str, list[StaticMatch]] = {}
    for item in data.get("results", []):
        filename = Path(item["path"]).name
        match = StaticMatch(
            tool="semgrep",
            rule_id=item["check_id"],
            file_path=filename,
            line=item["start"]["line"],
            message=item["extra"]["message"],
        )
        matches_by_file.setdefault(filename, []).append(match)

    return matches_by_file

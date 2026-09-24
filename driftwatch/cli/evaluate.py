"""python -m driftwatch.cli.evaluate

Runs the security review pipeline (the exact same code the live webhook
uses -- see review.orchestrator.analyze_and_decide) against a fixed set of
local fixtures with known ground truth, and reports precision/recall/F1/
false-positive-rate both before and after the validation layer, plus
validation pipeline stats. Requires real GEMINI_API_KEY (and DATABASE_URL,
transitively required by driftwatch.app.config even though this command
never touches Postgres) -- this measures the real pipeline, so it isn't
part of the mocked pytest suite.

Evaluation is fixture-level (per-fixture pass/fail: did >=1 finding get
posted for a fixture that should have one, or none for one that shouldn't),
not per-line -- exact LLM-reported line numbers aren't reproducible run to
run, so scoring at that granularity would be noisy rather than meaningful.
"""

import json
import logging
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from driftwatch.review.context import extract_chunks_from_source
from driftwatch.review.orchestrator import analyze_and_decide
from driftwatch.static_analysis.runner import run_static_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("driftwatch")

REPO_ROOT = Path(__file__).parent.parent.parent
FIXTURES_DIR = REPO_ROOT / "evaluation" / "fixtures"
EXPECTED_FINDINGS_PATH = REPO_ROOT / "evaluation" / "expected_findings.jsonl"
RESULTS_DIR = REPO_ROOT / "evaluation" / "results"

_CORROBORATING_SOURCES = {"semgrep", "bandit", "gitleaks"}


@dataclass
class ExpectedFixture:
    fixture: str
    file: str
    category: str
    expected: bool
    expected_issue: str | None


@dataclass
class FixtureResult:
    fixture: str
    expected: bool
    candidate_count: int
    accepted_count: int
    rejected_count: int
    needs_review_count: int
    static_corroborated_count: int
    latency_seconds: float


def load_expected_fixtures(path: Path = EXPECTED_FINDINGS_PATH) -> list[ExpectedFixture]:
    fixtures = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            fixtures.append(ExpectedFixture(**json.loads(line)))
    return fixtures


def run_fixture(expected: ExpectedFixture, fixtures_dir: Path = FIXTURES_DIR) -> FixtureResult:
    source_bytes = (fixtures_dir / expected.file).read_bytes()
    num_lines = max(len(source_bytes.decode("utf-8").splitlines()), 1)
    changed_ranges = [(1, num_lines)]

    start = time.perf_counter()
    chunks = extract_chunks_from_source(source_bytes, expected.file, changed_ranges, include_module_level=True)
    run_static_analysis(chunks)
    candidates, decided = analyze_and_decide(
        chunks,
        repository="driftwatch/evaluation",
        pr_title=f"Evaluation fixture: {expected.fixture}",
        pr_body="",
        pr_number=0,
    )
    latency = time.perf_counter() - start

    accepted = [finding for finding, _ in decided if finding.validation_status == "accepted"]
    rejected = [finding for finding, _ in decided if finding.validation_status == "rejected"]
    needs_review = [finding for finding, _ in decided if finding.validation_status == "needs_review"]
    static_corroborated = sum(
        1 for finding in accepted if any(e.source in _CORROBORATING_SOURCES for e in finding.evidence)
    )

    return FixtureResult(
        fixture=expected.fixture,
        expected=expected.expected,
        candidate_count=len(candidates),
        accepted_count=len(accepted),
        rejected_count=len(rejected),
        needs_review_count=len(needs_review),
        static_corroborated_count=static_corroborated,
        latency_seconds=latency,
    )


@dataclass
class ConfusionMatrix:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def false_positive_rate(self) -> float:
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) else 0.0


def compute_confusion_matrix(results: list[FixtureResult], posted_count) -> ConfusionMatrix:
    """posted_count(FixtureResult) -> int: how many findings would have
    been posted for that fixture under the policy being scored (e.g. any
    candidate at all, or only validated-accepted ones)."""
    matrix = ConfusionMatrix()
    for result in results:
        posted = posted_count(result) > 0
        if result.expected and posted:
            matrix.tp += 1
        elif result.expected and not posted:
            matrix.fn += 1
        elif not result.expected and posted:
            matrix.fp += 1
        else:
            matrix.tn += 1
    return matrix


@dataclass
class EvaluationReport:
    timestamp: str
    fixture_count: int
    before: ConfusionMatrix
    after: ConfusionMatrix
    total_candidates: int
    total_accepted: int
    total_rejected: int
    total_needs_review: int
    validation_acceptance_rate: float
    rejected_rate: float
    static_analysis_agreement_rate: float
    average_findings_per_fixture: float
    average_latency_seconds: float
    median_latency_seconds: float
    results: list[FixtureResult]


def build_report(results: list[FixtureResult]) -> EvaluationReport:
    # "Before validation": the most naive baseline -- post whatever the LLM
    # said, no filtering at all. "After": only validation-accepted findings.
    # Both computed from the same run's candidates/decided, no second LLM pass.
    before = compute_confusion_matrix(results, lambda r: r.candidate_count)
    after = compute_confusion_matrix(results, lambda r: r.accepted_count)

    total_candidates = sum(r.candidate_count for r in results)
    total_accepted = sum(r.accepted_count for r in results)
    total_rejected = sum(r.rejected_count for r in results)
    total_needs_review = sum(r.needs_review_count for r in results)
    total_static_corroborated = sum(r.static_corroborated_count for r in results)
    latencies = [r.latency_seconds for r in results]

    return EvaluationReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        fixture_count=len(results),
        before=before,
        after=after,
        total_candidates=total_candidates,
        total_accepted=total_accepted,
        total_rejected=total_rejected,
        total_needs_review=total_needs_review,
        validation_acceptance_rate=(total_accepted / total_candidates) if total_candidates else 0.0,
        rejected_rate=(total_rejected / total_candidates) if total_candidates else 0.0,
        static_analysis_agreement_rate=(total_static_corroborated / total_accepted) if total_accepted else 0.0,
        average_findings_per_fixture=(total_accepted / len(results)) if results else 0.0,
        average_latency_seconds=statistics.fmean(latencies) if latencies else 0.0,
        median_latency_seconds=statistics.median(latencies) if latencies else 0.0,
        results=results,
    )


_KNOWN_LIMITATIONS = [
    "Evaluation is fixture-level (per-fixture pass/fail), not per-line, since "
    "exact LLM-reported line numbers aren't reproducible run to run.",
    "Token/cost-per-review tracking is not implemented.",
    "Only the security engine is evaluated; bug/quality engines don't exist yet.",
    "Fixtures are local, purpose-built files, not real historical PRs -- chosen "
    "for reproducibility and speed. See docs/roadmap.md for the full rationale.",
]


def _matrix_dict(matrix: ConfusionMatrix) -> dict:
    return {
        "tp": matrix.tp,
        "fp": matrix.fp,
        "fn": matrix.fn,
        "tn": matrix.tn,
        "precision": round(matrix.precision, 3),
        "recall": round(matrix.recall, 3),
        "f1": round(matrix.f1, 3),
        "false_positive_rate": round(matrix.false_positive_rate, 3),
    }


def report_to_dict(report: EvaluationReport) -> dict:
    return {
        "timestamp": report.timestamp,
        "fixture_count": report.fixture_count,
        "before_validation": _matrix_dict(report.before),
        "after_validation": _matrix_dict(report.after),
        "total_candidates": report.total_candidates,
        "total_accepted": report.total_accepted,
        "total_rejected": report.total_rejected,
        "total_needs_review": report.total_needs_review,
        "validation_acceptance_rate": round(report.validation_acceptance_rate, 3),
        "rejected_rate": round(report.rejected_rate, 3),
        "static_analysis_agreement_rate": round(report.static_analysis_agreement_rate, 3),
        "average_findings_per_fixture": round(report.average_findings_per_fixture, 3),
        "average_latency_seconds": round(report.average_latency_seconds, 3),
        "median_latency_seconds": round(report.median_latency_seconds, 3),
        "known_limitations": _KNOWN_LIMITATIONS,
        "fixtures": [
            {
                "fixture": r.fixture,
                "expected": r.expected,
                "candidate_count": r.candidate_count,
                "accepted_count": r.accepted_count,
                "rejected_count": r.rejected_count,
                "needs_review_count": r.needs_review_count,
                "static_corroborated_count": r.static_corroborated_count,
                "latency_seconds": round(r.latency_seconds, 3),
            }
            for r in report.results
        ],
    }


def report_to_markdown(report: EvaluationReport) -> str:
    b, a = report.before, report.after
    expected_count = sum(1 for r in report.results if r.expected)
    clean_count = report.fixture_count - expected_count

    fixture_rows = "\n".join(
        f"| {r.fixture} | {'yes' if r.expected else 'no'} | {r.candidate_count} | {r.accepted_count} | "
        f"{r.rejected_count} | {r.needs_review_count} | {r.static_corroborated_count} | {r.latency_seconds:.2f}s |"
        for r in report.results
    )
    limitations = "\n".join(f"- {item}" for item in _KNOWN_LIMITATIONS)

    return f"""# DriftWatch Evaluation Report

Generated: {report.timestamp}
Fixtures: {report.fixture_count} ({expected_count} expected a finding, {clean_count} expected clean)

## Before vs. after validation

| | Precision | Recall | F1 | False positive rate |
|---|---:|---:|---:|---:|
| Before validation (any LLM candidate posted) | {b.precision:.2f} | {b.recall:.2f} | {b.f1:.2f} | {b.false_positive_rate:.2f} |
| After validation (only accepted posted) | {a.precision:.2f} | {a.recall:.2f} | {a.f1:.2f} | {a.false_positive_rate:.2f} |

## Validation pipeline stats

- Total candidate findings: {report.total_candidates}
- Accepted: {report.total_accepted}
- Rejected: {report.total_rejected}
- Needs review: {report.total_needs_review}
- Validation acceptance rate: {report.validation_acceptance_rate:.2f}
- Rejected rate: {report.rejected_rate:.2f}
- Static-analysis agreement rate (accepted findings with Semgrep/Bandit corroboration): {report.static_analysis_agreement_rate:.2f}
- Average findings per fixture: {report.average_findings_per_fixture:.2f}
- Average latency per fixture: {report.average_latency_seconds:.2f}s (median {report.median_latency_seconds:.2f}s)

## Per-fixture results

| Fixture | Expected | Candidates | Accepted | Rejected | Needs review | Static-corroborated | Latency |
|---|---|---:|---:|---:|---:|---:|---:|
{fixture_rows}

## Known limitations

{limitations}

*Do not treat these numbers as a general-purpose false-positive rate claim
beyond this fixture set -- spec §20 explicitly warns against that.*
"""


def main():
    expected_fixtures = load_expected_fixtures()
    logger.info(f"Running evaluation over {len(expected_fixtures)} fixtures...")

    results = []
    for expected in expected_fixtures:
        logger.info(f"Running fixture: {expected.fixture}")
        results.append(run_fixture(expected))

    report = build_report(results)
    report_dict = report_to_dict(report)
    report_md = report_to_markdown(report)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "runs").mkdir(parents=True, exist_ok=True)

    (RESULTS_DIR / "latest.json").write_text(json.dumps(report_dict, indent=2), encoding="utf-8")
    (RESULTS_DIR / "latest.md").write_text(report_md, encoding="utf-8")

    timestamp_slug = report.timestamp.replace("+00:00", "Z").replace(":", "")
    (RESULTS_DIR / "runs" / f"{timestamp_slug}.json").write_text(json.dumps(report_dict, indent=2), encoding="utf-8")

    print(report_md)
    logger.info(f"Report written to {RESULTS_DIR / 'latest.md'} and {RESULTS_DIR / 'latest.json'}")


if __name__ == "__main__":
    main()

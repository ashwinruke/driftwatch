# DriftWatch Evaluation Report

Generated: 2026-09-24T05:59:44.735257+00:00
Fixtures: 10 (4 expected a finding, 6 expected clean)

## Before vs. after validation

| | Precision | Recall | F1 | False positive rate |
|---|---:|---:|---:|---:|
| Before validation (any LLM candidate posted) | 1.00 | 1.00 | 1.00 | 0.00 |
| After validation (only accepted posted) | 1.00 | 1.00 | 1.00 | 0.00 |

## Validation pipeline stats

- Total candidate findings: 4
- Accepted: 4
- Rejected: 0
- Needs review: 0
- Validation acceptance rate: 1.00
- Rejected rate: 0.00
- Static-analysis agreement rate (accepted findings with Semgrep/Bandit corroboration): 1.00
- Average findings per fixture: 0.40
- Average latency per fixture: 14.10s (median 14.16s)

## Per-fixture results

| Fixture | Expected | Candidates | Accepted | Rejected | Needs review | Static-corroborated | Latency |
|---|---|---:|---:|---:|---:|---:|---:|
| sql_injection | yes | 1 | 1 | 0 | 0 | 1 | 14.02s |
| shell_injection | yes | 1 | 1 | 0 | 0 | 1 | 14.88s |
| hardcoded_secret | yes | 1 | 1 | 0 | 0 | 1 | 15.11s |
| unsafe_eval | yes | 1 | 1 | 0 | 0 | 1 | 13.07s |
| safe_parameterized_sql | no | 0 | 0 | 0 | 0 | 0 | 12.34s |
| safe_subprocess | no | 0 | 0 | 0 | 0 | 0 | 14.27s |
| config_constant_not_secret | no | 0 | 0 | 0 | 0 | 0 | 14.05s |
| password_param_safe_use | no | 0 | 0 | 0 | 0 | 0 | 14.75s |
| comment_only_change | no | 0 | 0 | 0 | 0 | 0 | 12.27s |
| harmless_refactor | no | 0 | 0 | 0 | 0 | 0 | 16.20s |

## Known limitations

- Evaluation is fixture-level (per-fixture pass/fail), not per-line, since exact LLM-reported line numbers aren't reproducible run to run.
- Token/cost-per-review tracking is not implemented.
- Only the security engine is evaluated; bug/quality engines don't exist yet.
- Fixtures are local, purpose-built files, not real historical PRs -- chosen for reproducibility and speed. See docs/roadmap.md for the full rationale.

*Do not treat these numbers as a general-purpose false-positive rate claim
beyond this fixture set -- spec §20 explicitly warns against that.*

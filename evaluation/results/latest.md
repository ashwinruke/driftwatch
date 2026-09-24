# DriftWatch Evaluation Report

Generated: 2026-09-23T07:49:16.374479+00:00
Fixtures: 10 (4 expected a finding, 6 expected clean)

## Before vs. after validation

| | Precision | Recall | F1 | False positive rate |
|---|---:|---:|---:|---:|
| Before validation (any LLM candidate posted) | 0.80 | 1.00 | 0.89 | 0.17 |
| After validation (only accepted posted) | 1.00 | 1.00 | 1.00 | 0.00 |

## Validation pipeline stats

- Total candidate findings: 6
- Accepted: 5
- Rejected: 0
- Needs review: 1
- Validation acceptance rate: 0.83
- Rejected rate: 0.00
- Static-analysis agreement rate (accepted findings with Semgrep/Bandit corroboration): 1.00
- Average findings per fixture: 0.50
- Average latency per fixture: 14.49s (median 13.68s)

## Per-fixture results

| Fixture | Expected | Candidates | Accepted | Rejected | Needs review | Static-corroborated | Latency |
|---|---|---:|---:|---:|---:|---:|---:|
| sql_injection | yes | 1 | 1 | 0 | 0 | 1 | 15.05s |
| shell_injection | yes | 1 | 1 | 0 | 0 | 1 | 15.51s |
| hardcoded_secret | yes | 2 | 2 | 0 | 0 | 2 | 24.29s |
| unsafe_eval | yes | 1 | 1 | 0 | 0 | 1 | 25.51s |
| safe_parameterized_sql | no | 0 | 0 | 0 | 0 | 0 | 7.39s |
| safe_subprocess | no | 0 | 0 | 0 | 0 | 0 | 10.25s |
| config_constant_not_secret | no | 0 | 0 | 0 | 0 | 0 | 10.59s |
| password_param_safe_use | no | 1 | 0 | 0 | 1 | 0 | 17.59s |
| comment_only_change | no | 0 | 0 | 0 | 0 | 0 | 6.39s |
| harmless_refactor | no | 0 | 0 | 0 | 0 | 0 | 12.31s |

## Known limitations

- Evaluation is fixture-level (per-fixture pass/fail), not per-line, since exact LLM-reported line numbers aren't reproducible run to run.
- Token/cost-per-review tracking is not implemented.
- Only the security engine is evaluated; bug/quality engines don't exist yet.
- Fixtures are local, purpose-built files, not real historical PRs -- chosen for reproducibility and speed. See docs/roadmap.md for the full rationale.

*Do not treat these numbers as a general-purpose false-positive rate claim
beyond this fixture set -- spec §20 explicitly warns against that.*

# Roadmap: DriftWatch → AI Code Reviewer

**Source of truth:** `driftwatch_ai_code_reviewer_agent_spec.md` (repo root)
is the full engineering spec (v1.1). This doc is a condensed, living summary
and status tracker — read the spec for exact wording, schemas, prompts, and
rationale. When they disagree, the spec wins; update this file to match.

## Vision

DriftWatch is evolving from a single-purpose documentation-drift bot into a
modular, evidence-grounded AI GitHub PR reviewer. The core differentiator:
**the LLM proposes candidate findings, but a deterministic validation layer
(AST evidence, static-analysis corroboration, location/diff relevance) — not
LLM confidence — decides what actually gets posted as a PR comment.**
Documentation drift becomes one review engine among several (security, bugs,
quality, documentation), all sharing one `ReviewEngine` interface, one
`Finding`/`Evidence` schema, and one validation/reporting pipeline.

## Status: Phase 0, 1 and 2 done, Phase 3 not started

The repository has been reorganized into a `driftwatch/` package (see
`CLAUDE.md`'s Architecture section for the current, accurate layout), and a
security review engine runs on `opened`/`synchronize`/`reopened` PR events.
Findings are now evidence-grounded: a real validation layer (syntactic
location/diff-relevance checks, offline Semgrep + Bandit corroboration,
scoring, deduplication) decides accept/needs_review/reject before anything
is posted — only `accepted` findings become inline comments. Documentation
drift is untouched throughout. Phases 1 and 2 are both confirmed live
end-to-end against a real PR, on top of spec §35's golden test cases
running through the real pipeline (see the Phase 2 report below). Nothing
from Phase 3 onward (evaluation framework, bug/quality engines, doc-drift
integration, dashboard) has been built yet.

## Current baseline → target module mapping

The spec's target layout (§8) is `src/driftwatch/{app,github,review,
analyzers,static_analysis,ast,validation,llm,reporting,observability,
persistence,cli}/`. Three deliberate deviations from the literal spec,
decided during Phase 0 planning:

- **No `src/` prefix, no `pyproject.toml`** — the package is
  `driftwatch/` at the repo root, imported via the working directory. There's
  no `render.yaml`/`Procfile` in this repo, so Render's actual build/start
  command isn't visible here; avoiding a packaging step keeps
  `pip install -r requirements.txt` + `uvicorn main:app` from the repo root
  working unmodified. Revisit if/when `python -m driftwatch.cli.evaluate`
  (Phase 3) or an actual install step is needed.
- **No `ReviewEngine` protocol yet** — that interface is explicitly spec'd
  as Phase 4 work (§36), not Phase 0/1. The doc-drift logic lives in
  `analyzers/documentation/` and the new security logic in
  `analyzers/security.py`, both called directly by their own orchestration
  path rather than through a shared engine interface yet — that happens
  when Phase 4 introduces the interface for all engines at once.
- **`pr_commenter.py`'s two responsibilities split differently than
  originally sketched**: generic posting → `github/comments.py`;
  doc-drift-specific comment formatting → `analyzers/documentation/formatting.py`.
  ~~`reporting/` proper arrives with Phase 4~~ — **correction, made during
  Phase 1**: spec's own recommended build order (§45) puts PR summary
  reporting right after inline comments, well before Phase 4, so
  `reporting/` (`comment_formatter.py`, `pr_summary.py`) was introduced in
  Phase 1 for the new security findings. Doc-drift's formatting stays where
  it is in `analyzers/documentation/formatting.py` (Rule 2 — no reason to
  move working code); a future phase can fold it into `reporting/` too if
  that turns out to be worth the churn.

Actual mapping (final, implemented):

| Old flat file | New location | Notes |
|---|---|---|
| `github_auth.py` | `driftwatch/github/auth.py` | unchanged logic |
| `main.py` (webhook routing/signature check) | `driftwatch/github/webhooks.py` | `main.py` is now a thin shim that just builds the FastAPI app and includes this router |
| `pr_commenter.py` | `driftwatch/github/comments.py` (posting) + `driftwatch/analyzers/documentation/formatting.py` (doc-drift comment formatting) | split, see above |
| `diff_extractor.py` | `driftwatch/ast/parser.py` (generic tree-sitter walk) + `driftwatch/review/context.py` (diff fetching + chunk-extraction glue) | |
| `doc_indexer.py` + `matcher.py` + `drafter.py` | `driftwatch/analyzers/documentation/{indexer,matcher,drafter}.py` | unchanged logic, `__init__.py` re-exports the public functions |
| `embeddings.py` | `driftwatch/llm/embeddings.py` | unchanged logic |
| `db.py` | `driftwatch/persistence/db.py` | unchanged logic; `db.py` at root is now a thin shim for `python db.py` |
| `retry.py` | `driftwatch/retry.py` | unchanged logic, no better-fitting package in the spec |
| `index_now.py` | unchanged location (root) | still a hardcoded one-off script, not a general CLI; only its imports were updated |
| (scattered `os.environ[...]` reads) | `driftwatch/app/config.py` | new: single source of truth for the required env vars, loads `.env` once |
| `driftwatch/github/client.py` | new | shared httpx helpers, factored out of near-identical GET/POST calls that used to be duplicated across the diff extractor, doc indexer, and PR commenter |

Phase 1 additions (all new, no old-file equivalent):

| New file | Purpose |
|---|---|
| `driftwatch/review/models.py` | `CandidateFinding`/`Finding`/`Evidence`/`StaticMatch` pydantic models (spec §9/§32) |
| `driftwatch/llm/provider.py` | `LLMProvider` protocol + `GeminiProvider`, using Gemini's structured JSON output instead of text parsing (spec §32) |
| `driftwatch/analyzers/security.py` | Security-engine prompt + LLM call, filters to `category == "security"` |
| `driftwatch/review/decision.py` | Phase-1 stub: confidence-floor filter, `CandidateFinding` → `Finding` (`validation_status="needs_review"` — honest, nothing validated it yet). Phase 2 replaces the internals, not the interface |
| `driftwatch/review/orchestrator.py` | `review_pull_request()`: wires context → security engine → decision → reporting for `opened`/`synchronize`/`reopened` |
| `driftwatch/reporting/comment_formatter.py`, `pr_summary.py` | Inline-finding and PR-summary markdown |
| `driftwatch/ast/parser.py` additions | `find_uncovered_ranges`, `extract_module_level_chunks`, `find_anchor_line`, `extract_imports`, `extract_surrounding_lines` |
| `driftwatch/github/comments.py` addition | `post_review_comment()` — line-anchored PR review comment (vs. the existing PR-level `post_pr_comment`) |

Phase 2 additions (all new, no old-file equivalent):

| New file | Purpose |
|---|---|
| `driftwatch/static_analysis/rules/security.yml` | Bundled, offline Semgrep ruleset (7 rules) covering the same categories as the security prompt — no `--config auto`/registry dependency at request time |
| `driftwatch/static_analysis/semgrep.py`, `bandit.py` | Subprocess adapters, JSON output → normalized `StaticMatch`; never raise, a failed/missing/timed-out tool just yields no corroboration |
| `driftwatch/static_analysis/executables.py` | Resolves a console-script executable relative to `sys.executable` rather than relying on PATH — needed because bare `"semgrep"`/`"bandit"` aren't reliably resolvable when Python is invoked without activating the venv first (found while testing this phase) |
| `driftwatch/static_analysis/runner.py` | Runs Semgrep + Bandit once per PR (not once per chunk — CLI startup alone is ~1-3s each) against a temp directory of all changed chunks, remaps line numbers back to each chunk |
| `driftwatch/validation/evidence.py` | Spec §16.1 Stages A (location) + B (diff relevance, syntactic only) + C (AST context) as one pass |
| `driftwatch/validation/rules.py` | Stage E: deterministic keyword heuristic for overstated-certainty wording, downgrades score, never a second LLM call |
| `driftwatch/validation/scoring.py` | `ValidationResult` + `compute_score()` (35/30/20/15 weights per spec §17) + `decide_status()` against `VALIDATION_ACCEPT_THRESHOLD`/`VALIDATION_REVIEW_THRESHOLD` |
| `driftwatch/validation/deduplication.py` | Stage F: collapse same-file/same-category/overlapping-line findings, keep the highest-scored |
| `driftwatch/validation/validator.py` | `validate(candidate, chunk) -> ValidationResult`, composing the above |

`driftwatch/review/decision.py`'s internals were replaced (same call
signature as Phase 1) to call `validate()` per candidate instead of a
confidence floor; `SECURITY_MIN_CONFIDENCE` was removed from
`app/config.py` — LLM confidence is now one weighted input (15%) into the
real score, not a standalone gate. `driftwatch/review/orchestrator.py` now
calls `run_static_analysis()` once per PR before deciding, and only posts
`accepted` findings. `reporting/pr_summary.py` and `comment_formatter.py`
now show real validation status/score/evidence instead of Phase 1's
blanket "unvalidated" disclaimer.

**Still net-new, no current equivalent (as of Phase 2):** bug/quality review
engines (§14.2/§14.3 — only security exists), evaluation framework +
labeled dataset (§21/§24), Langfuse observability (§25), relational schema
for review runs/findings/evidence (§28 — validation results aren't
persisted yet, just logged), Gitleaks/CodeQL, and the Next.js + FastAPI
multi-repo dashboard (§50-63). The validation layer (§16-19) and Semgrep/
Bandit adapters (§15) — previously net-new — were built in Phase 2.

## Phased plan

Condensed from spec §36 (phases 0-5) and §64 (adds phase 6). Do not start a
phase out of order — each has an explicit exit criterion in the spec.

| Phase | Goal | Exit criteria (see spec for full list) | Status |
|---|---|---|---|
| **0 — Repository assessment & refactor** | Prepare the existing repo: package boundaries, separate GitHub plumbing from the doc-drift engine, add typing/tests | Doc-drift flow still works; new architecture documented; no unnecessary rewrite | **Done** |
| 1 — GitHub PR review MVP | Webhooks for opened/synchronize/reopened, Python diff/context analysis, LLM provider interface, security engine first, inline comments + PR summary | A seeded vulnerability in a test PR produces one accurate inline finding | **Done — live-verified** |
| 2 — Validation layer | AST/location/diff-relevance validation, Semgrep + Bandit adapters, scoring, accept/reject/needs-review, deduplication | Same eval set run with validation on vs. off shows a measurable difference | **Done — golden cases + live-verified** |
| 3 — Evaluation & metrics | Labeled eval dataset, precision/recall/F1, false-positive rate, latency/cost metrics, `python -m driftwatch.cli.evaluate` | Produces `evaluation/results/latest.{md,json}` | Not started |
| 4 — Documentation drift integration | Move doc-drift into the common `ReviewEngine` interface, shared validation/reporting | Security/bug/quality/doc findings share one pipeline | Not started |
| 5 — Observability, CI/CD, recruiter demo | Langfuse tracing, Docker local setup, GitHub Actions, seeded demo PR, metrics report | A recruiter can understand what/why/how/results/repro from the repo alone | Not started |
| 6 — Web dashboard | Next.js/React + FastAPI read API: overview, repo list/detail, PR review page, finding evidence, observability, evaluation pages | User can navigate overview → repo → review → finding → evidence → metrics | Not started |

## Phase 0 report

Per spec §36 + §44:

1. ~~Inspect repository~~ — done (see `CLAUDE.md`).
2. Run existing tests — there were none; `test_auth.py` was a stale, broken
   manual script (deleted). Added `tests/unit/` (20 tests, pytest) covering
   the pure/deterministic logic instead: webhook signature verification,
   tree-sitter chunk matching (including the overlap-dedup case), markdown
   chunking (headings/paragraphs/fenced code), retry backoff, and
   private-key loading precedence.
3. ~~Document current architecture~~ — done (`CLAUDE.md`).
4. Differences between current architecture and the spec — see the mapping
   table above.
5. Minimal Phase 0 refactor implemented: `driftwatch/` package (root-level,
   no `src/`/`pyproject.toml` — see deviations above), GitHub plumbing
   separated from doc-drift logic, env vars centralized in
   `driftwatch/app/config.py`, `MAX_COMMENTS_PER_PR` made configurable
   (defaults to the previous hardcoded `3`).
6. Implemented — this refactor only, nothing from Phase 1 onward.
7. Tests pass: `pytest tests/unit -v` → 20 passed. Also verified `main.py`
   imports cleanly with the real `.env`, and a `TestClient` request to
   `/webhook` round-trips through real signature verification correctly
   (401 for an unsigned request).
8. **Risks / what remains**: no live end-to-end webhook test was run against
   real GitHub/Gemini/Postgres (would need live credentials + network, not
   exercised automatically). `MAX_COMMENTS_PER_PR` changed from a hardcoded
   constant to an env-configurable setting (default unchanged) — a
   deliberate, low-risk behavior addition beyond a pure move, done because
   spec §29 lists it as expected configuration. Everything else was a
   behavior-preserving move.

Phase 0's exit criteria are met. Do not start Phase 1 without re-checking
this file for any status drift since it was last updated.

## Phase 1 report

Security review engine implemented per the mapping table above. Two
correctness issues were found and fixed during design (see
`driftwatch/ast/parser.py`):

1. **Module-level findings** (e.g. a hardcoded secret as a top-level
   assignment) have no enclosing function/class, so the existing
   function/class-only chunk extraction would silently miss them —
   including one of the spec's own demo seeds (§40). Fixed with an opt-in
   fallback (`include_module_level=True`) that emits a pseudo-chunk for any
   changed lines not covered by a function/class chunk. Doc-drift's call
   site doesn't pass this flag, so its behavior is unchanged.
2. **Line-anchoring.** GitHub's line-comment API rejects a `line` that
   isn't part of the diff; a chunk's `start_line` (e.g. a `def` line) often
   isn't itself changed. Fixed with `find_anchor_line`, which picks the
   first actually-changed line inside the chunk.

**Known limitations** (documented, not silently skipped):
- No idempotency for duplicate webhook deliveries (spec §31) — needs the
  `review_runs` persistence Phase 2/3 introduces; a partial in-memory
  version wouldn't survive Render's free-tier spin-down anyway.
- Individual `POST /pulls/{pr}/comments` calls per finding, not the batched
  Reviews API — simpler, matches the codebase's existing one-call-per-comment
  style. Revisit if comment noise becomes a real problem.
- Every posted comment is explicitly labeled unvalidated (Phase 1, no
  independent evidence checking yet) in both the inline comment and the PR
  summary — intentional, not a placeholder to clean up later; it's the
  honest state of the pipeline until Phase 2 lands.

**Verified:** `pytest tests/unit tests/integration -v` → 39 passed,
including two integration tests (`tests/integration/test_security_review_flow.py`)
that drive a simulated `opened` PR webhook through signature verification →
orchestration → decision → posting with GitHub/Gemini calls mocked at the
`driftwatch.review.orchestrator` boundary, and two regression tests
(`tests/integration/test_doc_drift_regression.py`) confirming merged-PR
events still route to the untouched doc-drift handler and don't also
trigger a security review. `main.py` still imports cleanly against the real
`.env`.

**Live-tested and confirmed:** PR #13 ("Create test-driftwatch.py") against
`ashwinruke/Multithreaded_Web_Server` with a seeded vulnerability produced a
correct inline security finding + PR summary on the deployed Render
service. Phase 1's exit criterion is met.

**Unplanned but valuable side effect of the live test:** it surfaced a
pre-existing Render misconfiguration (`GITHUB_PRIVATE_KEY_PATH` held actual
key material instead of `GITHUB_PRIVATE_KEY` being set), which in turn
caused the key to be embedded in a `FileNotFoundError` message and logged.
Fixed in `driftwatch/github/auth.py`: `load_private_key()` now detects
key-shaped content in `GITHUB_PRIVATE_KEY_PATH` and fails with a clean
error instead (regression test in `tests/unit/test_github_auth.py`). The
exposed key was rotated and the Render env var corrected. This bug predates
Phase 0/1 — `load_private_key()`'s core logic was never changed by the
refactor, it just had never been exercised in production before Phase 1's
`opened`-PR trigger made the first real token request there.

## Phase 2 report

Validation layer implemented per the mapping table above. Every accepted
finding is now genuinely evidence-grounded: location/diff-relevance
checked syntactically, corroborated where possible against a real,
offline Semgrep + Bandit run, scored with LLM confidence capped at 15% of
the total (cannot alone cross `VALIDATION_ACCEPT_THRESHOLD`), deduplicated,
and only posted if the result is `accepted`.

**One correctness issue found and fixed during implementation:** bare
`"semgrep"`/`"bandit"` command names aren't reliably resolvable via
`subprocess.run` when the venv hasn't been "activated" (only affects
`PATH`, not which Python/console-scripts actually exist) — this surfaced
immediately as every static-analysis test silently returning zero matches.
Fixed with `static_analysis/executables.py`, which resolves each tool
relative to `sys.executable`'s directory instead of relying on `PATH`.
Worth calling out because the same class of issue could affect Render's
deployment environment depending on how its PATH is configured; this fix
makes that irrelevant either way.

**Demonstrating the phase's actual point** (spec §35's golden cases, now
real tests in `tests/integration/test_validator_golden_cases.py`, run
against the real validator + real offline Semgrep/Bandit):
- SQL injection (f-string built query) → **accepted** (Semgrep
  corroboration + diff overlap + LLM confidence).
- Unsafe `shell=True` → **accepted** (same reasoning).
- Safe parameterized query / safe list-form `subprocess.run` / a harmless
  refactor → no static-analysis corroboration for an injection-style issue
  (Bandit's generic low-severity "review this subprocess call" notices are
  expected and don't count as vulnerability corroboration).
- A finding with overstated wording ("this will always cause RCE,
  guaranteed") scores measurably lower than the same finding described
  accurately, even with identical underlying evidence.
- `tests/integration/test_security_review_flow.py` now demonstrates the
  concrete before/after: a finding that would have cleared Phase 1's bare
  0.6 confidence floor (0.7 confidence, no corroboration) now correctly
  lands in `needs_review` (score ≈0.655) and does **not** get posted.

**Known limitations** (documented, not silently skipped):
- No symbol/data-flow tracking — diff relevance is syntactic line-range
  overlap only, per spec's own caution against claiming data-flow proof
  from syntactic evidence alone.
- Static analysis runs against each chunk's own text as a standalone file,
  not the whole source file — loses cross-function context (e.g. a
  sanitizer defined elsewhere in the file). Acceptable for the target
  categories, which are mostly local/single-function patterns.
- `needs_review`/`rejected` findings are logged, not persisted — the
  `review_runs`/`findings` schema (spec §28) and the evaluation runner
  that will consume that history are both Phase 3 work.
- The bundled Semgrep ruleset (7 rules) doesn't cover path traversal —
  syntactic path-traversal patterns are prone to high false-positive rates
  without more context than a single-chunk scan gives; left to the LLM
  alone for now (no corroboration bonus for that category specifically).

**Verified:** `pytest tests/unit tests/integration -v` → 74 passed
(35 new since Phase 1), including real (offline, no network) Semgrep/Bandit
subprocess runs. `main.py` still imports cleanly against the real `.env`.

**Live-tested and confirmed** against `ashwinruke/Multithreaded_Web_Server`,
with a seeded `subprocess.run(x, shell=True)` finding correctly validated
(Bandit B602 + bundled Semgrep rule corroboration) and posted with the new
evidence/score-bearing comment format. Getting there surfaced four real
issues, none of them hypothetical — all found and fixed live, in order:

1. **`requirements.txt` broke Render's Linux build.** `pip freeze` on the
   local Windows dev venv flattened `pywin32`'s environment marker (a
   conditional dependency of `mcp`/`semgrep`, Windows-only), pinning it
   unconditionally. Fixed by restoring the `; sys_platform == "win32"`
   marker.
2. **Chunk extraction returned nothing, silently.** `review/context.py`
   skipped non-`.py`/removed files with no log line, so a `Files analyzed:
   0` result gave no clue why. Every skip path now logs its reason, plus a
   summary line.
3. **Webhook delivery timed out before Render could even respond.**
   GitHub's webhook delivery has a hard ~10s timeout; Phase 2 added real
   Semgrep/Bandit subprocess calls on top of the existing GitHub API +
   Gemini calls, all running synchronously inside the request handler —
   enough to exceed that timeout even when Render was awake. Fixed by
   moving the actual review to a FastAPI `BackgroundTask`, so the webhook
   acknowledges immediately and the review runs after the response is
   sent.
4. **Gemini returned a live 503** ("high demand"). Added `GroqProvider` +
   a provider-agnostic `FallbackProvider` (spec §6 asks for exactly this
   provider independence) — falls back to Groq's OpenAI-compatible API on
   any Gemini failure when `GROQ_API_KEY` is set, otherwise behaves exactly
   as before.

None of these were caught by the test suite beforehand, since none of them
are reachable from mocked GitHub/Gemini calls — a reminder that the local
suite (deliberately) doesn't substitute for a live pass against the real
deployment, GitHub App, and external APIs.

## Mandatory engineering rules (spec §42, condensed)

These apply to every phase, not just Phase 0:

- Inspect before modifying; don't assume the repo matches the spec exactly.
- Preserve working documentation-drift functionality unless the replacement
  is demonstrably equivalent or better tested.
- No giant files — keep webhook handling, orchestration, analysis,
  validation, persistence, and reporting in separate modules.
- Domain logic (especially the validator) must be unit-testable without
  network access or GitHub.
- Deterministic logic stays deterministic: never use an LLM for line
  validation, JSON parsing, deduplication, threshold comparisons, or basic
  AST checks.
- Don't hide uncertainty — use `needs_review`/`insufficient_evidence`
  instead of forcing a confident claim.
- Store concise evidence and conclusions, not hidden chain-of-thought.
- No hard-coded credentials; all secrets from env/config.
- Every dependency needs a documented purpose; every feature needs tests.

## MVP non-goals (spec §5, condensed)

Not in scope until explicitly revisited: every programming language (Python
first), a CodeQL/Semgrep replacement, autonomous merging/approval, a large
dashboard before Phase 6, a custom-trained LLM, a complex multi-agent
framework, dozens of LLM providers, or any claimed false-positive rate
without evaluation evidence to back it.

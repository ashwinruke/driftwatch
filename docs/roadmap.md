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

## Status: Phase 0 and Phase 1 done, Phase 2 not started

The repository has been reorganized into a `driftwatch/` package (see
`CLAUDE.md`'s Architecture section for the current, accurate layout), and a
security review engine now runs on `opened`/`synchronize`/`reopened` PR
events, posting **unvalidated** inline findings + a PR summary (validation
is Phase 2). Documentation drift is untouched throughout. Nothing from
Phase 2 onward (validation layer, bug/quality engines, evaluation,
dashboard) has been built yet.

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

**Net-new, no current equivalent:** validation layer (§16-19), static
analysis adapters for Semgrep/Bandit (§15), provider-independent LLM
interface (§6, §14), `Finding`/`Evidence` schema (§9), security/bug/quality
review engines (§14.1-14.3), evaluation framework + labeled dataset
(§21/§24), Langfuse observability (§25), relational schema for review runs/
findings/evidence (§28), and the Next.js + FastAPI multi-repo dashboard
(§50-63).

## Phased plan

Condensed from spec §36 (phases 0-5) and §64 (adds phase 6). Do not start a
phase out of order — each has an explicit exit criterion in the spec.

| Phase | Goal | Exit criteria (see spec for full list) | Status |
|---|---|---|---|
| **0 — Repository assessment & refactor** | Prepare the existing repo: package boundaries, separate GitHub plumbing from the doc-drift engine, add typing/tests | Doc-drift flow still works; new architecture documented; no unnecessary rewrite | **Done** |
| 1 — GitHub PR review MVP | Webhooks for opened/synchronize/reopened, Python diff/context analysis, LLM provider interface, security engine first, inline comments + PR summary | A seeded vulnerability in a test PR produces one accurate inline finding | **Code done — live test pending** |
| 2 — Validation layer | AST/location/diff-relevance validation, Semgrep + Bandit adapters, scoring, accept/reject/needs-review, deduplication | Same eval set run with validation on vs. off shows a measurable difference | Not started |
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

**Not yet done — needs a live test:** no real GitHub/Gemini call has been
made. The actual exit criterion (a seeded vulnerability in a real PR
producing an accurate inline finding) requires opening a test PR against
`ashwinruke/Multithreaded_Web_Server` with a seeded vulnerability and
confirming the App posts a correct inline comment — that's a manual,
credentialed step for the repo owner, not something run automatically.

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

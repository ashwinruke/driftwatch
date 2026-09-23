# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

DriftWatch is an autonomous GitHub bot (FastAPI webhook service) that detects
documentation drift in merged PRs: it matches changed code to the doc
sections that describe it using embeddings, and posts a PR comment flagging
outdated sections with an LLM-drafted fix. See README.md for full
architecture diagrams, the local setup walkthrough, and deployment notes —
this file focuses on things not already obvious from a read of the code.

## Project direction

This repo is expanding from a documentation-drift bot into a modular,
evidence-grounded **AI Code Reviewer** (security/bug/quality/doc-drift
review engines behind a validation layer, plus eventually a dashboard), per
`driftwatch_ai_code_reviewer_agent_spec.md` (repo root). See
`docs/roadmap.md` for the condensed phased plan, current-file→target-module
mapping, and phase status.

**Phases 0-2 are done** (refactor, security review MVP, validation layer)
— the flat-file layout is now the `driftwatch/` package described below, a
security review engine runs on `opened`/`synchronize`/`reopened` PR events
alongside the untouched, merge-triggered doc-drift pipeline, and every
posted finding is now evidence-grounded (syntactic location/diff checks +
real offline Semgrep/Bandit corroboration + scoring) before it's allowed to
post — see the security review pipeline below. Bug/quality engines,
persistence, evaluation, and the dashboard don't exist yet. Don't jump
ahead to later phases without checking `docs/roadmap.md` for current
status first.

Mandatory rules for any future work here (spec §42, applies to every
phase): inspect before modifying and don't assume the repo matches the spec
exactly; preserve working doc-drift functionality unless the replacement is
demonstrably equivalent or better tested; no giant files — keep webhook
handling, orchestration, analysis, validation, persistence, and reporting
in separate modules; domain logic (especially any future validator) must be
unit-testable without network/GitHub access; deterministic logic stays
deterministic — never use an LLM for line validation, JSON parsing,
deduplication, or threshold comparisons; don't hide uncertainty behind a
falsely confident claim; no hard-coded credentials; every dependency needs
a documented purpose and every feature needs tests.

## Commands

Setup (Windows):
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
docker run -d --name driftwatch-postgres -e POSTGRES_PASSWORD=password -e POSTGRES_DB=driftwatch -p 5432:5432 pgvector/pgvector:pg16
python db.py                    # creates the doc_sections table + ivfflat index
```

Run the webhook server:
```
uvicorn main:app --reload --port 8000
ngrok http 8000                 # expose it for GitHub webhook deliveries, local dev only
```

Build the initial doc index for a repo (one-off; edit the owner/repo args in
`index_now.py` before running — it's a hardcoded script, not a general CLI):
```
python index_now.py
```

Run the test suite:
```
pytest tests/unit tests/integration -v
```
There is no linter configured. `tests/unit/` covers pure/deterministic
logic (signature verification, tree-sitter chunk matching, markdown
chunking, retry backoff, private-key loading, decision filtering, comment
formatting, LLM-response parsing) — nothing that needs live
GitHub/Gemini/Postgres access. `tests/integration/` drives the FastAPI
`TestClient` through simulated webhook payloads with GitHub/Gemini calls
monkeypatched at the `driftwatch.review.orchestrator`/
`driftwatch.github.webhooks` module boundary. The root-level `conftest.py`
sets dummy env vars so `driftwatch.app.config` (see Architecture below) can
be imported during tests without a real `.env`; it also makes `import
driftwatch...` resolve without an editable install, since there's no
`pyproject.toml` here (deliberately — see `docs/roadmap.md`'s Phase 0
section for why).

Required env vars (`.env`, gitignored): `GITHUB_APP_ID`,
`GITHUB_WEBHOOK_SECRET`, `GITHUB_INSTALLATION_ID`, `GEMINI_API_KEY`,
`DATABASE_URL`, and either `GITHUB_PRIVATE_KEY_PATH` (local `.pem` file) or
`GITHUB_PRIVATE_KEY` (full key contents, used in production). Optional:
`MAX_COMMENTS_PER_PR` (default `3`), `VALIDATION_ACCEPT_THRESHOLD` (default
`0.75`) and `VALIDATION_REVIEW_THRESHOLD` (default `0.50`) — the score
cutoffs the validation layer uses to decide accepted/needs_review/rejected
(see Architecture below); `GROQ_API_KEY` and `GROQ_MODEL` (default
`openai/gpt-oss-120b`) — if `GROQ_API_KEY` is set, the security engine
falls back to Groq's OpenAI-compatible API when Gemini fails (added after
a live 503 from Gemini under high demand); if unset, Gemini is used alone,
same as before. All of these except the private-key pair are read once in
`driftwatch/app/config.py`.

Semgrep and Bandit (installed via `requirements.txt`) must be present as
CLI executables for the security pipeline's static-analysis corroboration
to work; both are invoked as subprocesses, resolved via
`driftwatch/static_analysis/executables.py` relative to the running
Python's own directory (not `PATH`) so they work whether or not the venv
was "activated."

## Architecture

`main.py` and `db.py` at the repo root are thin shims that exist only so
the two commands GitHub/Render and the README rely on
(`uvicorn main:app`, `python db.py`) keep working unchanged; all real logic
lives under `driftwatch/`. `index_now.py` stays a top-level one-off script
(see Gotchas).

```
driftwatch/
├── app/config.py          # single source of truth for env vars (loads .env once)
├── github/
│   ├── auth.py             # GitHub App JWT -> installation token exchange
│   ├── client.py            # shared httpx GET/POST helpers + auth headers
│   ├── webhooks.py           # FastAPI router: signature verification + event dispatch
│   └── comments.py           # post_pr_comment (PR-level) + post_review_comment (line-anchored)
├── ast/parser.py            # generic tree-sitter chunk extraction + line-range helpers
├── review/
│   ├── context.py            # diff fetching + chunk-extraction glue (uses ast/ + github/)
│   ├── models.py               # CandidateFinding / Finding / Evidence / StaticMatch models
│   ├── decision.py              # runs each candidate through validation.validator.validate()
│   └── orchestrator.py           # security-review pipeline: context -> static analysis ->
│                                 # engine -> decision -> reporting
├── analyzers/
│   ├── documentation/        # the doc-drift engine: indexer, matcher, drafter, formatting
│   └── security.py            # the security engine: prompt + LLM call
├── llm/
│   ├── embeddings.py          # Gemini embedding wrapper (doc-drift)
│   └── provider.py             # LLMProvider protocol + GeminiProvider (structured JSON output)
├── static_analysis/
│   ├── rules/security.yml    # bundled, offline Semgrep ruleset (no --config auto)
│   ├── semgrep.py             # subprocess adapter -> StaticMatch
│   ├── bandit.py               # subprocess adapter -> StaticMatch
│   ├── executables.py           # resolves the semgrep/bandit executables via sys.executable
│   └── runner.py                 # runs both tools once per PR, remaps line numbers to chunks
├── validation/
│   ├── evidence.py            # location + diff-relevance + AST-context checks
│   ├── rules.py                 # overstated-certainty wording heuristic
│   ├── scoring.py                 # ValidationResult + compute_score() + decide_status()
│   ├── deduplication.py             # collapses overlapping same-file/category findings
│   └── validator.py                  # validate(candidate, chunk) -> ValidationResult
├── reporting/
│   ├── comment_formatter.py    # inline-finding markdown (security/bug/quality findings)
│   └── pr_summary.py            # PR-level summary markdown
├── persistence/db.py        # PostgreSQL/pgvector connection + schema
└── retry.py                  # retry-with-backoff wrapper
```

Three independent webhook-triggered pipelines share one FastAPI router
(`driftwatch/github/webhooks.py`), all gated by HMAC signature verification
(`verify_signature`) against `GITHUB_WEBHOOK_SECRET`:

**1. PR-merge drift detection** (`pull_request` / closed+merged events):
```
review.context.extract_changed_chunks    -- fetch PR file diffs, parse hunk headers
                                            to find changed line ranges (ast.parser
                                            .changed_line_ranges), then use tree-sitter
                                            (ast.parser.find_enclosing_chunks) to find the
                                            enclosing function/class definitions that
                                            overlap those ranges (not raw diff lines)
        |
analyzers.documentation.find_stale_sections  -- embed the changed chunk (Gemini), cosine
                                            similarity search against doc_sections
                                            (pgvector), keep results >= SIMILARITY_THRESHOLD
        |
analyzers.documentation.draft_update      -- Gemini 2.5 Flash verifies the match is a real
                                            behavioral drift (not just topical similarity)
                                            and drafts a replacement for that section only
        |
github.comments.post_pr_comment           -- posts if verdict == OUTDATED, capped at
                                            MAX_COMMENTS_PER_PR (default 3) per PR via a
                                            comments_posted counter in webhooks.py
```
`draft_update` and `post_pr_comment` are both called through
`retry.with_retry` (exponential backoff, 3 attempts) since both hit external
APIs (Gemini / GitHub).

**2. Push-triggered doc re-index** (`push` events to the default branch
only, filtered by `.md` path suffix):
```
webhooks._handle_push diffs commits[].added/modified/removed for *.md paths
        |
analyzers.documentation.index_specific_files  -- incremental: deletes + re-inserts only
                                            the changed files' sections, or removes
                                            deleted files' sections entirely
```
This is distinct from `analyzers.documentation.index_repo_docs`, the
full-rebuild path used only by `index_now.py` for the initial index of a
repo. Both funnel through the same chunking logic (in
`analyzers/documentation/indexer.py`): `split_markdown_into_sections` splits
on `#` headings, then `_split_into_paragraphs` further splits each
heading's content into paragraph-level chunks (code fences kept intact as
one unit). This is why a single heading with several unrelated paragraphs
doesn't get matched/drafted as one oversized block — matching operates at
paragraph granularity, not heading granularity.

**3. Security review** (`pull_request` / opened, synchronize, reopened
events — separate from and unrelated to the merge-triggered pipeline above):
```
review.context.extract_changed_chunks(..., include_module_level=True)
                                          -- same chunk extraction as doc-drift, plus:
                                             a pseudo-chunk for changed lines not covered
                                             by any function/class (e.g. a hardcoded secret
                                             as a module-level assignment), an anchor_line
                                             per chunk, diff_ranges (for the validator's
                                             diff-relevance check), imports + a few lines of
                                             surrounding context
        |
static_analysis.runner.run_static_analysis  -- writes every chunk to a temp dir, runs the
                                             bundled offline Semgrep ruleset + Bandit ONCE for
                                             the whole PR (not per chunk -- CLI startup alone
                                             is ~1-3s each), attaches chunk["static_matches"]
        |
analyzers.security.analyze                -- builds a security-focused prompt per chunk,
                                             calls the LLM provider, filters to category
                                             == "security"
        |
llm.provider.<GeminiProvider or FallbackProvider>.generate_findings  -- Gemini structured
                                             JSON output (response_schema=list[CandidateFinding]).
                                             If GROQ_API_KEY is set, wrapped in a
                                             FallbackProvider that retries via Groq's
                                             OpenAI-compatible API on any Gemini failure
                                             (added after a live 503 from Gemini under high
                                             demand) -- otherwise Gemini alone. Both parse
                                             through the same pure, independently-testable
                                             parse_findings_response()
        |
review.decision.decide -> validation.validator.validate
                                           -- location + diff-relevance + AST-context checks
                                             (validation/evidence.py), static-analysis
                                             corroboration against chunk["static_matches"],
                                             an overstated-certainty wording penalty
                                             (validation/rules.py), then a weighted score
                                             (35% diff evidence / 30% static corroboration /
                                             20% AST consistency / 15% LLM confidence --
                                             confidence alone can never cross
                                             VALIDATION_ACCEPT_THRESHOLD) -> accepted /
                                             needs_review / rejected. Then
                                             validation.deduplication collapses overlapping
                                             same-file/category findings, keeping the
                                             highest-scored
        |
github.comments.post_review_comment       -- ONLY "accepted" findings get posted, one
                                             line-anchored inline comment each, capped at
                                             MAX_COMMENTS_PER_PR, then one PR-level summary
                                             via post_pr_comment (reporting/pr_summary.py)
                                             breaking down accepted/needs_review/rejected counts
```
`driftwatch/analyzers/security.py`'s prompt lists the target categories
from spec §14.1 (hardcoded secrets, unsafe command exec, SQL injection,
unsafe deserialization, path traversal, weak crypto, insecure subprocess
usage, dangerous dynamic eval) and instructs the model to be conservative
and never invent files/lines/functions — but the LLM is never the final
authority; only `validate()`'s output decides what gets posted.

## Key implementation details

- **Auth** (`github/auth.py`): GitHub App JWT (RS256, signed with the
  private key) exchanged for a short-lived installation token on every
  webhook delivery — not cached across requests. `load_private_key()`
  prefers the `GITHUB_PRIVATE_KEY` env var over `GITHUB_PRIVATE_KEY_PATH`,
  so production and local dev use the same code path. (This function reads
  `os.environ` directly rather than going through `app/config.py`, since
  the env-var-vs-file fallback is genuine conditional logic, not a plain
  required setting.)
- **GitHub client** (`github/client.py`): small shared helpers
  (`get`/`get_optional`/`get_content`/`post`) factored out of what used to
  be near-identical httpx calls repeated across the diff extractor, doc
  indexer, and PR commenter. `get_optional` doesn't raise on non-2xx, for
  the one caller (`index_specific_files`) that needs to distinguish a 404
  from other errors.
- **Chunk matching** (`ast/parser.py` + `review/context.py`): only `.py`
  files are considered; a tree-sitter node counts as "changed" if its line
  range overlaps *any* changed range from the diff, deduped by
  `(start_line, end_line)`.
- **Similarity threshold/top-K** live as constants at the top of
  `analyzers/documentation/matcher.py` (`SIMILARITY_THRESHOLD = 0.50`,
  `TOP_K = 3`) — tune here, not in the SQL.
- **Schema** (`persistence/db.py`): `doc_sections` table, `embedding
  vector(768)` (Gemini `gemini-embedding-001` truncated to 768 dims via
  `output_dimensionality` in `llm/embeddings.py`), ivfflat index with
  `lists = 10` — fine for the current small-corpus scale, would need
  revisiting for a large multi-repo index.
- Both the drift comment and the push-triggered re-index run inside broad
  `try/except Exception: logger.exception(...)` blocks in
  `github/webhooks.py`; `review/orchestrator.py`'s security-review pipeline
  has the same broad `except` — so a single failure never crashes the
  webhook handler or returns a non-200 to GitHub.
- **Line-anchoring** (`ast/parser.py`'s `find_anchor_line`): GitHub's
  `POST /pulls/{pr}/comments` rejects a `line` that isn't part of the diff.
  A chunk's `start_line` (e.g. a function's `def` line) is often *not*
  itself a changed line, so the orchestrator always posts at
  `chunk["anchor_line"]` (the first actually-changed line inside the
  chunk), not `chunk["start_line"]`.
- **`include_module_level` is opt-in** on `review.context.extract_changed_chunks`
  (default `False`). Only the security orchestrator passes `True`; doc-drift's
  call site is unchanged, so its behavior is identical to before Phase 1.
  When `True`, it also attaches `anchor_line`/`diff_ranges`/`imports`/
  `context_before`/`context_after` to every chunk, function/class and
  module-level alike.
- **Structured LLM output** (`llm/provider.py`): the security engine uses
  Gemini's `response_schema=list[CandidateFinding]` + `response_mime_type
  ="application/json"` rather than text parsing — deliberately different
  from doc-drift's `drafter.py`, which keeps its original line-based
  `VERDICT:`/`DRAFT:`/`REASON:` parsing untouched (no reason to touch
  working code that isn't part of the change being made).
- **Static analysis runs against each chunk's own text as a standalone
  file**, not the whole source file (`static_analysis/runner.py`) — loses
  cross-function context (e.g. a sanitizer defined elsewhere in the file)
  in exchange for one Semgrep/Bandit invocation per PR instead of per file.
  A documented limitation, not an oversight; revisit if it causes missed
  corroboration in practice.
- **Executable resolution** (`static_analysis/executables.py`): Semgrep/
  Bandit are invoked via `Path(sys.executable).parent / "<tool>.exe"`
  rather than bare command names on `PATH`. This mattered in practice —
  every static-analysis test silently returned zero matches until this
  existed, because `PATH` doesn't reliably include the venv's `Scripts/`
  directory unless the venv was "activated" first (directly invoking
  `venv\Scripts\python.exe` doesn't set `PATH`). Falls back to `PATH`
  resolution if the direct path doesn't exist.
- **LLM confidence cannot alone cross the accept threshold** by
  construction (`validation/scoring.py`): its weight is fixed at 15% of
  the total score, so `confidence=1.0` with zero other evidence
  contributes only `0.15` — well under `VALIDATION_ACCEPT_THRESHOLD`'s
  default `0.75`. This is spec §17's explicit requirement, enforced by the
  weight itself rather than a separate check.
- **No static-analysis match does not mean rejected.** `validation/validator.py`
  treats missing corroboration as one lower-weighted signal among several,
  not a veto — a finding can still be `accepted` on strong diff/AST
  evidence plus high LLM confidence alone if it clears the threshold.
- **LLM fallback** (`llm/provider.py`): `FallbackProvider` is provider-agnostic
  by design — it only knows both providers implement `generate_findings(prompt)
  -> list[CandidateFinding]`, and retries via the fallback on *any* exception
  from the primary. Groq's `json_object` mode (unlike Gemini's
  `response_schema`) doesn't enforce a specific shape, so `GroqProvider`
  appends a JSON-schema description (generated from `CandidateFinding
  .model_json_schema()`, not hand-duplicated) to the prompt, and asks for
  `{"findings": [...]}` rather than a bare array — `parse_findings_response()`
  accepts both shapes so both providers share the identical parsing path.
- **No `pyproject.toml`/`src/` layout, deliberately**: Render's actual
  build/start command isn't visible from this repo (no `render.yaml`/
  `Procfile`), so the package lives at `driftwatch/` (root-level, not
  `src/driftwatch/`) and is imported via the working directory rather than
  an editable install — this keeps `pip install -r requirements.txt` +
  `uvicorn main:app` from the repo root working exactly as before. See
  `docs/roadmap.md` if this needs revisiting later (e.g. for
  `python -m driftwatch.cli.evaluate` in a future phase).

## Gotchas

- The repo root contains a real `.pem` private key
  (`driftwatch-dev.*.private-key.pem`) and a `.env` file — both are covered
  by `.gitignore` (`*.pem`, `.env`). Never remove those gitignore entries or
  commit either file.
- `index_now.py` has a hardcoded test repo
  (`ashwinruke/Multithreaded_Web_Server`) — edit before reusing against a
  different repo. (The old `test_auth.py`, which had the same hardcoded
  repo and was already broken/stale, was deleted during the Phase 0
  refactor — superseded by `tests/unit/test_github_auth.py`.)
- `ast/` (the package) shares its name with Python's stdlib `ast` module,
  and `static_analysis/semgrep.py` / `static_analysis/bandit.py` share
  their names with the real installed `semgrep`/`bandit` packages. Neither
  is an actual collision: nothing here does `import ast`/`import semgrep`/
  `import bandit` (tree-sitter is used for AST parsing; Semgrep/Bandit are
  only ever invoked as subprocesses), and these are always imported via
  their full `driftwatch.*` path, never bare.
- The bundled Semgrep ruleset (`static_analysis/rules/security.yml`, 7
  rules) doesn't cover path traversal — syntactic patterns for it are
  prone to high false positives without more context than a single-chunk
  scan provides. Left to the LLM alone for now; no corroboration bonus for
  that category specifically.
- **No idempotency yet for duplicate webhook deliveries** on the security
  pipeline (spec §31) — a GitHub retry on the same `synchronize` event
  could double-post comments. Deliberately deferred to when Phase 2/3's
  `review_runs` persistence exists; documented as a known limitation in
  `docs/roadmap.md` rather than half-solved with something that wouldn't
  survive Render's free-tier spin-down anyway.
- **Live-verified**: PR #13 against `ashwinruke/Multithreaded_Web_Server`
  with a seeded vulnerability produced a correct inline finding + PR
  summary on the deployed Render service. That live test also surfaced a
  pre-existing Render env var misconfiguration (`GITHUB_PRIVATE_KEY_PATH`
  held key material instead of `GITHUB_PRIVATE_KEY` being set), which
  briefly leaked the private key into logs via an unguarded exception
  message — fixed in `github/auth.py` (`load_private_key()` now refuses
  key-shaped content in `GITHUB_PRIVATE_KEY_PATH` with a clean error), key
  rotated, Render env var corrected. See `docs/roadmap.md`'s Phase 1 report
  for the full writeup.

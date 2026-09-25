# DriftWatch

![CI](https://github.com/ashwinruke/driftwatch/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)

An evidence-grounded AI code reviewer for GitHub pull requests — started as
a documentation-drift bot, now a security reviewer and a doc-drift detector
sharing one validation pipeline. **The LLM proposes candidate findings; a
deterministic validation layer decides what actually gets posted.**

## What this is

Two review engines watch your pull requests:

- **Security review** (`opened`/`synchronize`/`reopened` events) — extracts
  changed functions/classes via tree-sitter, runs offline Semgrep + Bandit
  against them, and asks an LLM to flag security issues (hardcoded secrets,
  SQL/command injection, unsafe deserialization, path traversal, weak
  crypto, dangerous `eval`).
- **Documentation drift** (merged-PR events) — embeds each changed function,
  finds the doc sections that describe it via cosine similarity, and asks an
  LLM to verify whether the change actually makes that section outdated
  (and draft a fix if so).

Both engines emit the same `CandidateFinding` shape into one shared
validation → deduplication → reporting pipeline before anything is allowed
to post as a PR comment. Neither engine's LLM output is trusted directly —
see below.

## Why this is interesting

- **The LLM never gets the final vote.** Every candidate finding is scored
  from four independent signals — diff-relevance (35%), static-analysis
  corroboration via Semgrep/Bandit (30%), AST-location consistency (20%),
  and LLM confidence (15%) — and only `accepted` findings get posted.
  LLM confidence's weight is capped at 15% *by construction*, so a
  confidence of `1.0` with zero other evidence scores `0.15` — nowhere near
  the `0.75` acceptance threshold. A finding can't get through on the
  model simply asserting it's sure.
- **A real evaluation harness, not anecdotal claims.** `python -m
  driftwatch.cli.evaluate` runs the exact production code path against a
  labeled fixture set and reports precision/recall/F1/false-positive rate
  before vs. after validation — see [Evaluation results](#evaluation-results)
  below and the full committed report at
  [`evaluation/results/latest.md`](evaluation/results/latest.md).
- **Live-verified against a real GitHub repo, not just unit-tested.** A
  seeded vulnerability in a real PR produced a correct inline finding on
  the deployed service; a real merged PR that contradicted an indexed doc
  section produced a correct documentation finding in the same shared
  format, coexisting on the same PR as an unrelated security finding
  without interference; a real PR triggered a Langfuse trace on the
  deployed Render service with correct nested LLM generations and
  metadata. Full write-ups, including two real bugs a live test actually
  caught (a leaked private key in an error message, a doc-index/database
  mismatch), are in [`docs/roadmap.md`](docs/roadmap.md).
- **Built to survive a real 503, not just the happy path.** When
  `GROQ_API_KEY` is set, a Gemini failure automatically falls back to
  Groq's OpenAI-compatible API mid-review — added after Gemini actually
  returned one in production under load.
- **CI on every push**: lint (Ruff), a security self-scan of the codebase
  itself (Bandit + the project's own bundled Semgrep ruleset), and the
  full test suite.
- **Optional, zero-overhead LLM observability.** Set three Langfuse env
  vars and every review run becomes a traced span with nested LLM
  generations; leave them unset and the tracing decorators don't wrap
  anything at all — not even a no-op — so there's no cost to leaving it off.
- **Two supported local dev paths**: a manual venv + standalone Postgres
  container, or `docker compose up --build` for the whole stack with live
  reload.

## How it works

**Security review** (opened/synchronize/reopened):
```
PR event -> extract changed chunks (tree-sitter, + module-level pseudo-chunks)
                              |
              Semgrep + Bandit once per PR (offline, bundled ruleset)
                              |
                  LLM proposes candidate findings per chunk
                              |
        validation: diff evidence + AST location + static corroboration
              + wording heuristic -> weighted score -> accept/reject
                              |
              deduplication (line-overlap) -> inline comments + PR summary
```

**Documentation drift** (PR merged):
```
PR merged -> extract changed chunks
                              |
        embed each chunk -> cosine similarity vs. indexed doc sections
                              |
          LLM verifies real behavioral drift + drafts a replacement
                              |
        validation: pass-through (evidence already gathered above)
                              |
           deduplication (exact title) -> PR comment + PR summary
```

A separate, simpler path re-indexes markdown files incrementally whenever
they're pushed to the default branch, so the doc index doesn't need a full
manual rebuild after every doc change.

## Example output

Illustrative — built from the real `sql_injection` evaluation fixture and
the actual comment template (`driftwatch/reporting/comment_formatter.py`);
real score/evidence values vary run to run:

> ### 🟠 Security: SQL injection via unsanitized f-string interpolation
>
> **Issue**
>
> `user_id` is interpolated directly into a SQL query string via an
> f-string and passed to `cursor.execute()`, allowing SQL injection if
> `user_id` originates from untrusted input.
>
> **Evidence**
>
> - Diff: the f-string query is built and executed within the changed lines (`sql_injection.py:2`)
> - Semgrep: matched the bundled ruleset's SQL-injection rule (`sql_injection.py:2`)
> - AST: `cursor.execute(query)` runs the tainted `query` variable in the same function
>
> **Suggested fix**
>
> ```python
> query = "SELECT * FROM users WHERE id = %s"
> cursor.execute(query, (user_id,))
> ```
>
> **Validation**
>
> Status: `accepted`
> Static analysis: corroborated
> Validation score: 0.91
> LLM confidence: 0.85

## Evaluation results

From the committed [`evaluation/results/latest.md`](evaluation/results/latest.md)
(10 fixtures: 4 expected a finding, 6 expected clean):

| | Precision | Recall | F1 | False positive rate |
|---|---:|---:|---:|---:|
| Before validation (any LLM candidate posted) | 1.00 | 1.00 | 1.00 | 0.00 |
| After validation (only accepted posted) | 1.00 | 1.00 | 1.00 | 0.00 |

Static-analysis agreement rate on accepted findings: 1.00. Average latency
per fixture: ~14s. This is a small, purpose-built local fixture set chosen
for reproducibility and speed, not a sample of real historical PRs — see
the full report for per-fixture detail and known limitations, and don't
treat these numbers as a general-purpose false-positive-rate claim beyond
this set.

## Architecture

```
driftwatch/
├── app/config.py            # env vars, loaded once
├── github/                  # webhooks, auth, GitHub API client, comment posting
├── ast/parser.py            # tree-sitter chunk extraction + line-anchoring
├── review/                  # ReviewEngine protocol, orchestrator, decision, models
├── analyzers/
│   ├── security.py          # security engine: prompt + LLM call
│   └── documentation/       # doc-drift: indexer, matcher, drafter, engine adapter
├── llm/provider.py          # LLMProvider protocol: Gemini, Groq fallback
├── static_analysis/         # Semgrep + Bandit adapters, run once per PR
├── validation/              # evidence checks, scoring, deduplication
├── reporting/                # inline-finding + PR-summary markdown formatting
├── observability/tracing.py  # optional Langfuse tracing (span + generation decorators)
├── persistence/                # review_runs/findings/evidence schema + write path
├── dashboard/                 # read-only API (schemas/queries/api) for the dashboard/ frontend
└── cli/evaluate.py           # local evaluation harness, same code path as production
```

`dashboard/` (repo root, sibling to `driftwatch/`) is a separate Next.js/
TypeScript app calling the API above — see [Dashboard](#dashboard) below.

## Tech stack

- FastAPI — webhook receiver + orchestration
- GitHub App — authenticated API access (JWT → installation token)
- tree-sitter — AST-based code chunking (function/class level, not raw lines)
- Google Gemini — embeddings, structured-JSON findings, doc-fix drafting
- Groq (OpenAI-compatible API) — automatic fallback on Gemini failure
- Semgrep + Bandit — offline static-analysis corroboration
- PostgreSQL + pgvector — vector storage and similarity search
- Langfuse — optional LLM observability (traces, nested generations)
- Docker + Docker Compose — containerized local dev
- GitHub Actions — CI (lint, security self-scan, tests) on every push
- Render — hosted deployment (web service + managed Postgres)

## Status & roadmap

| Phase | What | Status |
|---|---|---|
| 0 — Repo refactor | Package boundaries, tests, typing | Done |
| 1 — Security review MVP | Webhooks, chunking, LLM provider, inline comments | Done — live-verified |
| 2 — Validation layer | AST/diff checks, Semgrep+Bandit, scoring, dedup | Done — live-verified |
| 3 — Evaluation & metrics | Labeled fixtures, precision/recall/F1 | Done — real report generated |
| 4 — Documentation drift integration | Shared validation/reporting pipeline | Done — live-verified |
| 5 — Observability, CI/CD, recruiter demo | CI, Docker, Langfuse, README | Done — Langfuse live-verified on Render |
| 6 — Web dashboard | Overview/repo/review/finding pages | Foundation + golden path done — Observability/Evaluation/Analytics pages, auth deferred |

Full phase-by-phase detail, live-test write-ups, and known limitations:
[`docs/roadmap.md`](docs/roadmap.md). Full engineering spec:
[`driftwatch_ai_code_reviewer_agent_spec.md`](driftwatch_ai_code_reviewer_agent_spec.md).

## Local setup

Prerequisites: Python 3.12+, Docker Desktop, a GitHub App registered on a
test repo, a free Gemini API key from https://aistudio.google.com/apikey.

Create and activate a virtual environment, then install dependencies:

    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt

Start the vector database:

    docker run -d --name driftwatch-postgres -e POSTGRES_PASSWORD=password -e POSTGRES_DB=driftwatch -p 5432:5432 pgvector/pgvector:pg16
    python db.py

Create a `.env` file:

    GITHUB_APP_ID=
    GITHUB_WEBHOOK_SECRET=
    GITHUB_PRIVATE_KEY_PATH=
    GITHUB_INSTALLATION_ID=
    GEMINI_API_KEY=
    DATABASE_URL=postgresql://postgres:password@localhost:5432/driftwatch
    # Optional
    GROQ_API_KEY=
    LANGFUSE_PUBLIC_KEY=
    LANGFUSE_SECRET_KEY=
    LANGFUSE_BASE_URL=

For local development, `GITHUB_PRIVATE_KEY_PATH` points to your `.pem`
file. In production, `GITHUB_PRIVATE_KEY` (the full key contents) is used
instead — both are supported. `GROQ_API_KEY` enables the Gemini→Groq
fallback; the three `LANGFUSE_*` vars enable optional tracing (see
[Why this is interesting](#why-this-is-interesting)) — leave all of these
unset and the corresponding feature is simply inactive.

Index a repo's docs (one-time, or whenever you want a full rebuild):

    python index_now.py

Run the webhook server:

    uvicorn main:app --reload --port 8000

Expose it for GitHub's webhook (dev only):

    ngrok http 8000

Run the test suite and linter (also run automatically on every push/PR via
GitHub Actions, see the badge above):

    pytest tests/unit tests/integration -v
    ruff check driftwatch tests main.py db.py index_now.py conftest.py

### Alternative: Docker Compose

Instead of the manual venv + `docker run` + `uvicorn` steps above,
`docker compose up --build` starts the app and Postgres together, with
live code reload and a persistent data volume. You still need the `.env`
file described above, with one difference: set `GITHUB_PRIVATE_KEY` (the
full key contents) instead of `GITHUB_PRIVATE_KEY_PATH` — the `.pem` file
itself is deliberately excluded from the built image (`.dockerignore`,
same reasoning as `.gitignore`), so a file path won't resolve inside the
container. `DATABASE_URL` is overridden automatically in
`docker-compose.yml` to point at the `postgres` service rather than
`localhost`.

    docker compose up --build

The app is then reachable at `http://localhost:8000`, same as running
`uvicorn` directly. `docker compose down` stops it (add `-v` to also drop
the Postgres data volume). If you already have a standalone
`driftwatch-postgres` container running from the manual setup above, stop
it first (`docker stop driftwatch-postgres`) to free port 5432.

## Dashboard

A separate read-only Next.js app (`dashboard/`) shows review history,
findings, and validation evidence across repositories — overview → repo →
PR review → finding evidence, per spec §63's priority order. It calls the
backend's `/api/v1/*` routes (`driftwatch/dashboard/`), which need at
least one review run persisted to show anything (a real PR review, or a
webhook simulation). See [`dashboard/README.md`](dashboard/README.md) for
setup; short version:

    cd dashboard
    cp .env.local.example .env.local
    npm install && npm run dev

No auth yet (MVP — see `docs/roadmap.md`'s Phase 6 report for what's
deferred: Observability/Evaluation/Analytics pages, dashboard auth, a full
review-run state machine).

## Deployment notes

Deployed on Render's free tier for demonstration purposes:
- The web service spins down after 15 minutes of inactivity; the first
  request after idle time can take up to a minute to respond, which may
  cause a GitHub webhook delivery to time out. GitHub retries failed
  deliveries automatically, or you can manually redeliver from the
  GitHub App's Recent Deliveries page.
- The free PostgreSQL database expires 30 days after creation, with a
  14-day grace period before deletion. Re-provisioning requires
  re-running the indexing step against a fresh `DATABASE_URL`.
- The private key is stored as a `GITHUB_PRIVATE_KEY` environment
  variable in production, rather than a local file path.

## Project structure

| File | Purpose |
|------|---------|
| main.py | Thin entrypoint: builds the FastAPI app, includes the webhook router |
| db.py | Thin entrypoint for `python db.py` (schema setup) |
| index_now.py | One-off script to build the initial doc index for a repo |
| driftwatch/app/config.py | Single source of truth for env vars |
| driftwatch/github/auth.py | GitHub App JWT + installation token exchange (file or env-var key) |
| driftwatch/github/client.py | Shared GitHub API httpx helpers |
| driftwatch/github/webhooks.py | Webhook routes (PR merges, opens/syncs, doc pushes), signature verification, event dispatch |
| driftwatch/github/comments.py | Posts a PR-level comment or a line-anchored review comment |
| driftwatch/ast/parser.py | tree-sitter chunk extraction, module-level fallback, line-anchoring, import/context extraction |
| driftwatch/review/context.py | Fetches PR diffs and extracts changed code chunks |
| driftwatch/review/engine.py | ReviewEngine protocol + ReviewContext, shared by every review engine |
| driftwatch/review/models.py | CandidateFinding / Finding / Evidence schema |
| driftwatch/review/decision.py | Runs each candidate through the validation layer, then dedup |
| driftwatch/review/orchestrator.py | Security-review pipeline: context → engines → decision → reporting |
| driftwatch/analyzers/documentation/ | The doc-drift engine: indexer, matcher, drafter + engine.py (adapts a verdict into a CandidateFinding) |
| driftwatch/analyzers/security.py | The security-review engine: prompt + LLM call + the SecurityEngine wrapper |
| driftwatch/llm/embeddings.py | Gemini embedding wrapper (doc-drift) |
| driftwatch/llm/provider.py | LLMProvider protocol + GeminiProvider + GroqProvider + FallbackProvider |
| driftwatch/static_analysis/ | Offline Semgrep + Bandit adapters, run once per PR |
| driftwatch/validation/ | The validation layer: location/diff/AST checks, scoring, dedup |
| driftwatch/reporting/ | Inline-finding and PR-summary markdown formatting |
| driftwatch/observability/tracing.py | Optional Langfuse tracing: span + generation decorators |
| driftwatch/persistence/db.py | PostgreSQL/pgvector connection + schema (doc_sections + review_runs/findings/evidence) |
| driftwatch/persistence/review_store.py | Writes a review run's data (findings, evidence, validation scores, comments) for the dashboard |
| driftwatch/dashboard/ | Dashboard read API: schemas.py (Pydantic models), queries.py (SQL), api.py (FastAPI router) |
| dashboard/ | The Next.js/TypeScript dashboard frontend (repo root, separate from `driftwatch/`) |
| driftwatch/retry.py | Retry-with-backoff wrapper for transient API failures |
| driftwatch/cli/evaluate.py | `python -m driftwatch.cli.evaluate` — runs the security pipeline against `evaluation/fixtures/`, reports precision/recall/F1/false-positive rate before vs. after validation |
| evaluation/ | Local fixtures + ground truth + generated metrics reports (`results/latest.{md,json}`) |
| tests/unit/, tests/integration/ | pytest coverage — pure logic, plus webhook flows with GitHub/Gemini mocked |

## License

[MIT](LICENSE)

# DriftWatch

![CI](https://github.com/ashwinruke/driftwatch/actions/workflows/ci.yml/badge.svg)

Autonomous GitHub bot that detects documentation drift in merged PRs.
Watches merged pull requests, matches changed code to the doc sections
that reference it using embeddings, and posts a PR comment flagging
outdated sections with an LLM-drafted suggested update.

## Status
Core pipeline complete and deployed. End-to-end flow working:
merged PR -> changed function/class extracted (tree-sitter) -> matched
against indexed docs via semantic similarity (pgvector) -> LLM verifies
the match and drafts a fix -> suggestion posted as a PR comment.

Docs also re-index automatically and incrementally whenever markdown
files are pushed to the default branch, so the doc index stays current
without manual intervention.

## How it works
1. A PR is merged -> GitHub webhook fires (signature-verified)
2. The bot fetches the diff and uses tree-sitter to identify which
   functions/classes actually changed (not just raw diff lines)
3. Each changed function is embedded and compared against a pre-indexed
   corpus of markdown doc sections using cosine similarity (pgvector)
4. Sections above a similarity threshold are passed to an LLM, which
   verifies whether the change actually makes the doc outdated (filtering
   out topically-similar but behaviorally-unaffected sections)
5. If genuinely outdated, the LLM drafts a corrected version of just that
   section, and DriftWatch posts it as a PR comment (capped per PR to
   avoid spamming large PRs)
6. Separately, pushes to the default branch that touch markdown files
   trigger an incremental re-index of just the changed files

## Architecture

PR merged -> webhook -> diff extraction (tree-sitter)
                              |
                     embed changed function
                              |
                similarity search vs. doc index (pgvector)
                              |
                   flag stale sections (score >= threshold)
                              |
                    LLM verifies + drafts fix
                              |
                   posted as PR comment (capped per PR)

Push to default branch (markdown files changed)
                              |
              incremental re-index of just those files
                              |
                    doc index stays current

Docs are indexed at the paragraph level (not just per heading), so a
single doc section with multiple unrelated paragraphs doesn't get
matched or drafted as one oversized block.

## Stack
- FastAPI - webhook receiver + orchestration
- GitHub App - authenticated API access (JWT -> installation token)
- tree-sitter - AST-based code chunking (function/class level, not raw lines)
- Google Gemini Embedding API - free-tier embeddings, no local compute needed
- Gemini 2.5 Flash - LLM verification + drafted update suggestions
- PostgreSQL + pgvector - vector storage and similarity search
- Render - hosted deployment (web service + managed Postgres)
- Docker + ngrok - local development only

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

## Local setup

Prerequisites: Python 3.12+, Docker Desktop, a GitHub App registered
on a test repo, a free Gemini API key from https://aistudio.google.com/apikey

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

For local development, `GITHUB_PRIVATE_KEY_PATH` points to your `.pem`
file. In production, `GITHUB_PRIVATE_KEY` (the full key contents) is
used instead - both are supported.

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

## Project structure

The bot is being expanded into a modular AI code reviewer; see
`docs/roadmap.md` and `driftwatch_ai_code_reviewer_agent_spec.md` for the
full plan and phase status. As of Phase 4, the code lives under `driftwatch/`:

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
| driftwatch/review/engine.py | ReviewEngine protocol + ReviewContext (shared by security and, conceptually, documentation) |
| driftwatch/review/models.py | CandidateFinding / Finding / Evidence schema |
| driftwatch/review/decision.py | Runs each candidate through the validation layer, then dedup |
| driftwatch/review/orchestrator.py | Security-review pipeline: context → engines → decision → reporting |
| driftwatch/analyzers/documentation/ | The doc-drift engine: indexer, matcher, drafter (unchanged) + engine.py (adapts a verdict into a CandidateFinding) |
| driftwatch/analyzers/security.py | The security-review engine: prompt + LLM call + the SecurityEngine wrapper |
| driftwatch/llm/embeddings.py | Gemini embedding wrapper (doc-drift) |
| driftwatch/llm/provider.py | LLMProvider protocol + GeminiProvider (structured JSON output) |
| driftwatch/static_analysis/ | Offline Semgrep + Bandit adapters, run once per PR |
| driftwatch/validation/ | The validation layer: location/diff/AST checks, scoring, dedup |
| driftwatch/reporting/ | Inline-finding and PR-summary markdown formatting |
| driftwatch/persistence/db.py | PostgreSQL/pgvector connection + schema |
| driftwatch/retry.py | Retry-with-backoff wrapper for transient API failures |
| driftwatch/cli/evaluate.py | `python -m driftwatch.cli.evaluate` — runs the security pipeline against `evaluation/fixtures/`, reports precision/recall/F1/false-positive rate before vs. after validation |
| evaluation/ | Local fixtures + ground truth + generated metrics reports (`results/latest.{md,json}`) |
| tests/unit/, tests/integration/ | pytest coverage — pure logic, plus webhook flows with GitHub/Gemini mocked |

## Roadmap

DriftWatch is being expanded from a documentation-drift bot into a modular
AI code reviewer (security/bug/quality review engines behind a validation
layer, evaluation metrics, and eventually a multi-repo dashboard). See
`docs/roadmap.md` for the phased plan and current status, and
`driftwatch_ai_code_reviewer_agent_spec.md` for the full engineering spec.
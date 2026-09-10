# DriftWatch

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

## Project structure

| File | Purpose |
|------|---------|
| main.py | FastAPI app, webhook routes (PR merges + doc pushes), event filtering, comment cap |
| github_auth.py | GitHub App JWT + installation token exchange (file or env-var key) |
| diff_extractor.py | Fetches PR diffs, uses tree-sitter to find changed functions/classes |
| db.py | PostgreSQL/pgvector connection + schema |
| embeddings.py | Gemini embedding wrapper |
| doc_indexer.py | Crawls markdown docs, splits into paragraph-level sections, embeds, stores; supports full and incremental re-index |
| matcher.py | Embeds changed code, runs similarity search against doc index |
| drafter.py | LLM verification + drafted update suggestion (Gemini 2.5 Flash) |
| pr_commenter.py | Formats and posts the drift comment to the PR |
| retry.py | Retry-with-backoff wrapper for transient API failures |
| index_now.py | One-off script to build the initial doc index for a repo |

## Roadmap (v2.0, not yet started)

- Multi-repo support (config table of enrolled repos)
- Drift history dashboard
- Slack notifications alongside PR comments
- JS/TS support via tree-sitter-javascript / tree-sitter-typescript
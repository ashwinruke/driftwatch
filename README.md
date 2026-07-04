# DriftWatch

Autonomous GitHub bot that detects documentation drift in merged PRs.
Watches merged pull requests, matches changed code to the doc sections
that reference it using embeddings, and posts a PR comment flagging
outdated sections with an LLM-drafted suggested update.

## Status
In development. Core detection pipeline works end-to-end:
merged PR -> changed function/class extracted -> matched against indexed
docs via semantic similarity -> logged as potential drift.

Next: LLM-drafted update suggestions, posted back as an actual PR comment.

## How it works
1. A PR is merged -> GitHub webhook fires (signature-verified)
2. The bot fetches the diff and uses tree-sitter to identify which
   functions/classes actually changed (not just raw diff lines)
3. Each changed function is embedded and compared against a pre-indexed
   corpus of markdown doc sections using cosine similarity (pgvector)
4. Sections above a similarity threshold are flagged as potentially outdated
5. Coming next: an LLM drafts a suggested update, posted as a PR comment

## Architecture

PR merged -> webhook -> diff extraction (tree-sitter)
                              |
                     embed changed function
                              |
                similarity search vs. doc index (pgvector)
                              |
                   flag stale sections (score >= threshold)

Docs are indexed separately: markdown files are pulled from the repo,
split into heading-level sections, embedded, and stored, independent
of the webhook flow, so re-indexing docs doesn't require a code change.

## Stack
- FastAPI - webhook receiver + orchestration
- GitHub App - authenticated API access (JWT -> installation token)
- tree-sitter - AST-based code chunking (function/class level, not raw lines)
- Google Gemini Embedding API - free-tier embeddings, no local compute needed
- PostgreSQL + pgvector (via Docker) - vector storage and similarity search
- ngrok - local webhook tunneling for development

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

Index a repo's docs (one-time, or whenever docs change significantly):

    python index_now.py

Run the webhook server:

    uvicorn main:app --reload --port 8000

Expose it for GitHub's webhook (dev only):

    ngrok http 8000

## Project structure

| File | Purpose |
|------|---------|
| main.py | FastAPI app, webhook route, event filtering |
| github_auth.py | GitHub App JWT + installation token exchange |
| diff_extractor.py | Fetches PR diffs, uses tree-sitter to find changed functions/classes |
| db.py | PostgreSQL/pgvector connection + schema |
| embeddings.py | Gemini embedding wrapper |
| doc_indexer.py | Crawls markdown docs, splits into sections, embeds, stores |
| matcher.py | Embeds changed code, runs similarity search against doc index |
| index_now.py | One-off script to (re)build the doc index for a repo |
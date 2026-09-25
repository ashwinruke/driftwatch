# DriftWatch Dashboard

Read-only Next.js dashboard for DriftWatch's review history: repositories,
PR reviews, findings, and validation evidence. Calls the FastAPI backend's
`/api/v1/*` routes (`driftwatch/dashboard/` in the repo root) — see the
root [`README.md`](../README.md) and [`docs/roadmap.md`](../docs/roadmap.md)'s
Phase 6 report for the full architecture and what's deliberately deferred
(auth, Observability/Evaluation/Analytics pages).

## Local setup

Requires the backend running separately (`uvicorn main:app` from the repo
root, with a Postgres reachable at its `DATABASE_URL` — see the root
README's Local setup section) and populated with at least one review run
(open a real PR against a repo the bot reviews, or run a webhook
simulation) so the pages have something to show.

```bash
cp .env.local.example .env.local   # points at http://localhost:8000 by default
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Pages

```
/                                          Overview: KPI cards + findings-by-category/severity charts
/repositories                              Repository list
/repositories/[id]                         Repository detail + recent review runs
/repositories/[id]/reviews/[reviewId]      PR review: stats + findings table
/findings/[id]                             Finding detail: evidence + validation breakdown
```

## Deployment

Deploy to Vercel and set `NEXT_PUBLIC_API_URL` to the deployed backend's
URL, plus `DASHBOARD_ORIGIN` on the backend (Render) to this app's Vercel
URL, so CORS allows it through.

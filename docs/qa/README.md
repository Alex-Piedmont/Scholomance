# Migration-QA artifacts

Read-only audit of Discovery drawer + DetailPage rendering vs. DB content,
across every university in the `technologies` table. See
`docs/plans/2026-04-23-002-fix-migration-qa-drawer-parity-plan.md` for
architecture and rationale.

## Files

- `samples-<date>.json` / `samples-latest.json` — 15 stratified records
  per university (AU-1). Deterministic seed per university code; stable
  across runs on the same DB.
- `db-coverage-<date>.{json,md}` / `db-coverage-latest.json` — per-record,
  per-section has_data/empty/malformed from AU-2.
- `playwright-drawer-<date>.worker-<N>.json` — per-worker Playwright
  results for the drawer spec (AU-4). `<N>` is the Playwright
  `TEST_WORKER_INDEX`.
- `playwright-detail-<date>.worker-<N>.json` — same, DetailPage spec (AU-5).
- `migration-matrix-<date>.{json,md}` / `migration-matrix-latest.{json,md}`
  — merged gap matrix (AU-9). Human-readable markdown + machine JSON.

## Commands

```bash
# Full pipeline (sample -> DB audit -> Playwright drawer+detail -> matrix)
tech-scraper migration-qa run

# Rerun matrix only (after Playwright partials update)
tech-scraper migration-qa matrix

# Single-university sweep (fast fix-loop)
tech-scraper migration-qa run --skip-sample --skip-audit --grep uni-jhu

# Production sign-off against the live Vercel URL (AU-10)
tech-scraper migration-qa run --target prod
```

## Regenerating

1. `migration-qa sample` — snapshots the current DB. Deterministic but the
   sample set changes when the DB gains/loses records.
2. `migration-qa audit-db` — evaluates each sampled record against the
   section catalog. Updates `db-coverage-latest.json`.
3. Playwright (from `web/`): `npm run test:e2e` starts the dev server
   pointed at the prod API (per `web/.env.local`) and runs both spec
   files. Workers write partial JSON under `docs/qa/`.
4. `migration-qa matrix` merges everything into the dated + `-latest`
   artifacts.

## Read-only invariant

No command in this pipeline writes to `technologies` or any scraper-managed
table. Parser/renderer fixes land on future scrapes; retroactive DB
updates require explicit user approval (see CLAUDE.md).

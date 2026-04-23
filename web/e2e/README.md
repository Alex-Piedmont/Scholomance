# Migration-QA e2e suite

Playwright specs that audit the Discovery drawer and DetailPage against the
per-record sample list produced by `tech-scraper migration-qa sample`.

## Local (dev server + prod API, fastest iterate loop)

```
cp .env.local.example .env.local   # points VITE_API_URL at Railway
npm run test:e2e
```

The Playwright config auto-starts `npm run dev`. On fail it keeps the trace,
screenshot, and HTML report under `playwright-report/` (git-ignored).

## Production (Vercel URL, for AU-10 sign-off)

```
PLAYWRIGHT_BASE_URL=https://web-one-lake-22.vercel.app npm run test:e2e
```

When `PLAYWRIGHT_BASE_URL` is set the config skips `webServer` and asserts
directly against the deployed build.

## Artifacts

- `playwright-report/` — HTML report, open with `npx playwright show-report`.
- `test-results/` — trace, screenshot, video on failure.
- `../docs/qa/playwright-drawer-<date>.json` — custom reporter output (AU-4).
- `../docs/qa/playwright-detail-<date>.json` — custom reporter output (AU-5).

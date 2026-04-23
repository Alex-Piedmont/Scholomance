---
date: 2026-04-23
plan: 002
type: fix
source: Direct request (branch: Migration-QA)
depth: Deep
status: Draft
---

# Plan: Migration QA — Drawer Parity and Field Coverage Across All Universities

## Context Summary

The new Phronesis Discovery landing page (commit `621d644`, polished by `2a83030`) introduced a slide-over drawer (`DiscoveryDrawer`) as the primary record-viewing surface. The drawer currently renders only ~10 of the ~46 fields exposed by `parseRawData`, while the still-routed full `DetailPage` at `/technology/:uuid` renders ~40 via `ContentSections` + `SidePanel` + `AssessmentSection`. `TechCard` does not link to `DetailPage`; users can only reach it by typed URL.

DB and API are intact. Evidence from direct query of JHU C18050 (`uuid=be9a2b26-…`): `raw_data` holds 20 populated keys including `inventors` (5 items), `development_stage`, `advantages` (as string, not array), `full_description`, and `publications` (as array of `{text}` objects). The "only Description on Vercel" symptom is a drawer-rendering gap plus several silent parser drops, not data loss.

Institutional knowledge (synthesized from commits `13da7ff`, `fd7b8f6`, `25359ff`, `876bfa3`, `d7a754e`) names the exact failure class: scrapers occasionally emit fields as strings where the parser expects arrays; `parseRawData` adds `Array.isArray` guards ad hoc, and unprotected `.map()` blanks the page via React crashes. A global `ErrorBoundary` already mitigates the blank-page worst case.

Stack: FastAPI + SQLAlchemy + Postgres (37 scrapers registered in `src/scrapers/registry.py`); React 19 + Vite 7 + TypeScript 5.9 (no existing test infra — no Vitest, no Playwright, no CI). Python CLI conventions are Click + Rich + Loguru via `src/cli.py`, backed by `db.get_session()` in `src/database.py`. No `scripts/` or `src/qa/*` directory yet; audit code lives as Click subcommands.

The user has directed:
- Audit **every** university present in `technologies` (union of registry codes and `SELECT DISTINCT university`).
- 15 stratified records per university; fewer if the catalog is smaller.
- Drawer must reach DetailPage parity — every rendered UI section on DetailPage must also be reachable from the drawer.
- Local dev server pointed at the prod Railway API for the iterative loop; final sign-off run against the live Vercel URL, gated on deploy SHA matching HEAD.
- Fix parser/renderer only. No retroactive DB writes. Scraper code changes allowed (future-only).
- Playwright is the verification mechanism. No `.github/` CI exists; tests must be runnable via `npm run test:e2e` and optionally invoked by a top-level audit command.

## Requirements Trace

| Requirement | Source | Atomic Unit(s) |
|---|---|---|
| R1: Inventory every university + record count, including DB-only codes not in registry | User directive | AU-1 |
| R2: Sample 15 representative records per university, stratified across time + development_stage | User directive | AU-1 |
| R3: Emit a per-university DB-to-UI-section coverage report distinguishing "no data" from "data exists" | User directive | AU-2 |
| R4: Install Playwright against a monorepo `web/` subdir with env-driven baseURL (local vs. Vercel) | User directive + best practices | AU-3 |
| R5: Assert every UI section the DetailPage renders is also rendered by the drawer for each sampled record | User answer: drawer must reach parity | AU-4, AU-8 |
| R6: Assert DetailPage `/technology/:uuid` still renders fully (deep-link regression baseline) | User directive | AU-5 |
| R7: Normalize shape variants (string↔array, HTML wrapping, alternate keys) in `parseRawData` so silent drops cannot occur | Investigation finding + learnings | AU-6 |
| R8: Expand `DiscoveryDrawer` to render the union of sections rendered by `ContentSections` + `SidePanel` | User answer: drawer = DetailPage parity | AU-7, AU-8 |
| R9: Merge DB audit + Playwright results into a per-university pass/fail matrix (university × section) | User directive | AU-9 |
| R10: Run the full suite against production (Vercel) gated on deploy SHA, commit the final matrix | User directive | AU-10 |
| R11: No destructive DB operations; scraper/parser/renderer fixes only | CLAUDE.md + user answer | All AUs (invariant); explicit check in AU-9 |

## Scope Boundaries

**In scope:**
- Python CLI subcommand(s) for inventory, sampling, and DB-side section-coverage audit
- Playwright bootstrap, drawer spec, detail-page spec, artifact pipeline
- `parseRawData.ts` normalization + drawer rendering parity
- Sharing render components between drawer and DetailPage to prevent future drift
- Committed gap matrix artifact under `docs/qa/`

**Out of scope:**
- Any `UPDATE` / `INSERT` to `technologies.raw_data` (CLAUDE.md)
- Re-scraping existing records (no scraper runs triggered by this plan)
- Adding CI (`.github/workflows/`) — suite runs on demand
- Rewriting scrapers for shape consistency (parser absorbs variants; scraper code fixes are deferred)
- Product changes to DetailPage beyond what's needed for section-component sharing
- Introducing Vitest / unit-test tooling for React components
- Extending the existing `/qa` review tool (`QASample`, `QACorrection`) — this audit is separate and read-only
- Rendering `AssessmentSection` inside the drawer — assessments are a heavier workflow surface that remains DetailPage-only; drawer parity covers `ContentSections` + `SidePanel` sections only

## Atomic Units

### AU-1: Sample generator CLI — every university, stratified 15
- [ ] **Goal:** A single CLI command emits a deterministic JSON sample file covering every university present in the database.
**Requirements:** R1, R2
**Dependencies:** None
**Files:**
- `src/qa/__init__.py` — new package
- `src/qa/migration_sampler.py` — new; builds the sample per-university
- `src/cli.py` — register `migration-qa sample` subcommand, Rich summary table
- `docs/qa/.gitkeep` — ensure output directory exists
**Approach:**
Enumerate universities as `union(registry_codes, SELECT DISTINCT university FROM technologies)`. For each university, fetch all `technologies` rows with `raw_data IS NOT NULL` ordered by `first_seen`. Pick samples in four strata: oldest, newest, 1 record per distinct `raw_data->>'development_stage'` (capped by remaining slots), then fill with `random.Random(seed=university_code)` picks until 15 or exhausted. When a university has fewer than 15 populated records, sample `min(15, count)` and mark the university `FULL_COVERAGE`. Exclude `raw_data IS NULL` rows from sampling but report their count in the inventory summary. Emit `docs/qa/samples-<ISO-date>.json` with shape `{ generated_at, seed, universities: [{ code, total_records, null_raw_data, sampled: [{ uuid, tech_id, first_seen, stratum, raw_data_keys }] }] }`. Also write/overwrite `docs/qa/samples-latest.json` as an exact copy (fresh pointer that downstream specs resolve to without date juggling). Print a Rich table with per-university totals + sample size; exit non-zero if any required university yields zero samples.
**Test Scenarios:**
- Small catalog (e.g. Texas State with <15 records): emits `min(count, 15)` and flags `FULL_COVERAGE`.
- Registry-only university with zero DB rows: reported in summary as `empty` and excluded from samples.
- DB-only code not in registry: still included in the sample output.
- Re-running the command: identical UUIDs selected (deterministic seed).
**Verification:**
`docs/qa/samples-<date>.json` exists, covers ≥37 universities (registry count), each entry has a `sampled[]` array of length `min(15, total_records)`, strata are represented where available. Rich summary table sums record counts that match `SELECT university, COUNT(*) FROM technologies GROUP BY university`.

---

### AU-2: DB-side section coverage auditor
- [ ] **Goal:** Compute a per-record, per-UI-section "data available?" matrix from the DB and emit a per-university summary.
**Requirements:** R3, R11
**Dependencies:** AU-1
**Files:**
- `src/qa/section_catalog.py` — new; static mapping of UI sections to the raw_data keys / top-level columns that feed them (mirror of `DiscoveryDrawer` + `ContentSections` + `SidePanel`)
- `src/qa/migration_audit.py` — new; reads samples JSON, walks each record, produces coverage rows
- `src/cli.py` — register `migration-qa audit-db` subcommand
**Approach:**
Define UI sections as a single source of truth in `section_catalog.py`. Each entry: `{"id": "inventors", "label": "Inventors", "sources": [{"type": "raw_data", "key": "inventors", "accepted_shapes": ["array_of_strings", "newline_string", "comma_string"]}], "surfaces": ["drawer", "detail"]}`. The closed set of shape tokens for this plan is exactly: `array_of_strings`, `array_of_objects`, `newline_string`, `comma_string`, `html_string`, `plain_string`, `object` — every source declares one or more from this set; anything not matching is `malformed`. For each sampled record, evaluate whether each section has data under any accepted shape — result is `has_data | empty | malformed`. Write a per-university markdown report `docs/qa/db-coverage-<date>.md` and a machine-readable `db-coverage-<date>.json` keyed `{university: {uuid: {section_id: status}}}`. The Rich summary table shows, per university, how many sampled records have data for each section; highlight sections where ≥1 record is `malformed` (these are the parser-gap candidates for AU-6). This AU does not hit the UI — it is purely a DB-to-catalog comparison. The catalog file is consumed again by AU-9 to merge with Playwright results.
**Test Scenarios:**
- JHU C18050: `advantages` catalog accepts `plain_string` → status is `has_data`. Inventors array of 5 → `has_data`. `publications` (array of `{text}` objects, matched by `array_of_objects`) → `has_data`.
- Record with `raw_data = {}`: every section reports `empty`.
- Record with `raw_data.inventors = "John, Jane"` and catalog accepts `comma_string`: `has_data`. Same value with catalog accepting only `array_of_strings`: `malformed` (flag for AU-6 to decide whether to coerce).
**Verification:**
`docs/qa/db-coverage-<date>.md` lists every sampled university. JHU C18050 shows Inventors=has_data, Development Stage=has_data, Advantages=has_data (or malformed if catalog restricts to arrays — drives AU-6 scope). Totals line sums to `sum(len(samples) per university)`.

---

### AU-3: Playwright bootstrap in web/
- [ ] **Goal:** Install `@playwright/test` ^1.59, configure env-driven baseURL, scaffold `web/e2e/` with a passing smoke test.
**Requirements:** R4
**Dependencies:** None
**Files:**
- `web/package.json` — add `@playwright/test` devDependency, `test:e2e` and `test:e2e:prod` scripts
- `web/playwright.config.ts` — new; chromium-only, `baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173'`, `webServer` block conditional on baseURL not being set, `workers: process.env.CI ? 4 : '50%'`, `fullyParallel: true`, `trace/screenshot/video: retain-on-failure` / `only-on-failure`, `reporter: [['html', { open: 'never' }], ['list']]`
- `web/e2e/smoke.spec.ts` — new; navigates to `/`, asserts the Phronesis header is visible
- `web/.gitignore` — add `test-results/`, `playwright-report/`, `playwright/.cache/`
- `web/.env.local.example` — new; documents `VITE_API_URL=https://api-production-10c1.up.railway.app/api` as the dev-against-prod-API recipe
**Approach:**
Install via `npm init playwright@latest` in `web/`, accept chromium-only, no CT. Retain the generated config shape. Add the top-level-await pattern that AU-4 will use to fetch the samples JSON at collection time — keep the smoke test free of that so it proves the toolchain independently. The `webServer` block launches `npm run dev` only when `PLAYWRIGHT_BASE_URL` is unset. Document the recipe (`cp .env.local.example .env.local && npm run test:e2e`) in a short `web/e2e/README.md`.
**Test Scenarios:**
- `cd web && npm run test:e2e` with no env vars: Vite boots, smoke test passes.
- `PLAYWRIGHT_BASE_URL=https://web-one-lake-22.vercel.app npm run test:e2e`: bypasses `webServer`, smoke test passes against Vercel.
**Verification:**
`npm run test:e2e` reports 1 passing test; HTML report lands under `web/playwright-report/` and is git-ignored. No dependencies hoisted into root `node_modules`.

---

### AU-4: Playwright drawer parity spec
- [ ] **Goal:** For every sampled record, open the drawer from the Discovery page and assert every UI section whose DB row has data is rendered.
**Requirements:** R5, R11
**Dependencies:** AU-1, AU-2, AU-3
**Files:**
- `web/e2e/drawer-parity.spec.ts` — new; top-level `await fs.readFile` of the samples JSON (path via `PLAYWRIGHT_SAMPLES` env, default `../docs/qa/samples-latest.json`), then `for (const { code, sampled } of universities) test.describe(code, () => { for (const tech of sampled) test(...) })`
- `web/e2e/fixtures/section-selectors.ts` — new; maps `section_id` (mirror of AU-2 catalog) to a DOM selector function `(page) => Locator` scoped to the drawer (`page.locator('.drawer.is-open')`)
- `web/e2e/fixtures/crash-detection.ts` — new; exports `assertDrawerAlive(page, tech)` which verifies `tech.title` renders inside the drawer before per-section assertions run
- `web/src/components/Discovery/TechCard.tsx` — add `data-uuid={tech.uuid}` attribute on the card button so Playwright can click a stable selector without depending on search results
**Approach:**
Tests are generated from samples JSON at collection time using top-level-await. Also loads the AU-2 `db-coverage-latest.json` to know which sections each record is expected to show. Each test: navigate to `/`, call `page.locator('[data-uuid="<uuid>"]').scrollIntoViewIfNeeded().click()` (deterministic, not dependent on search state or the `?openTech=` deep-link that AU-8 adds later), wait for `.drawer.is-open`, call `assertDrawerAlive` to distinguish crash from missing field, then loop over the section catalog: for each section marked `has_data` in the DB audit JSON for that record, call the selector and `expect.soft(locator).toBeVisible()`. Soft assertions let one failing section surface all others without short-circuiting the per-record report. Custom reporter writes `docs/qa/playwright-drawer-<date>.json`. Run with `fullyParallel: true`, `workers: '50%'` locally; expect a first diagnostic run to fail for ~most records (drawer is thin today) — that failure IS the signal that drives AU-7/AU-8. If a sampled UUID is not present in the Discovery listing for any reason (filtered out, pagination cutoff), the spec reports `UNREACHABLE` distinct from `fail` — resolved later by AU-8's `?openTech=` deep-link surface.
**Test Scenarios:**
- JHU C18050 run-1 (before AU-7): drawer reports missing Inventors, Development Stage (or passes if drawer already renders them); missing Full Description, Applications, Background, etc.
- Any university run-1: drawer never crashes (title present) — if a crash is seen, it is logged as `CRASH` rather than per-section missing.
- Record with `raw_data = {}`: no per-section assertions run; test passes trivially.
**Verification:**
`docs/qa/playwright-drawer-<date>.json` exists, contains per-record `{status: pass|fail|crash, missing_sections: [...]}`. Failures map 1:1 to sections the drawer does not currently render — confirming the coverage hypothesis rather than a spec bug.

---

### AU-5: Playwright DetailPage regression spec
- [ ] **Goal:** For every sampled record, direct-navigate to `/technology/:uuid` and assert every UI section whose DB row has data is rendered. Establishes the parity target that the drawer must match.
**Requirements:** R6, R11
**Dependencies:** AU-1, AU-2, AU-3
**Files:**
- `web/e2e/detail-page.spec.ts` — new; data-driven like AU-4 but scoped to the full page
- `web/e2e/fixtures/section-selectors.ts` — extend with detail-page-scoped variants where DOM differs
**Approach:**
Same data source as AU-4. Navigate via `await page.goto('/technology/' + tech.uuid)`. Selectors scope to `main` rather than `.drawer`. A crash helper asserts the page renders the title and no `ErrorBoundary` fallback is shown. Custom reporter writes `docs/qa/playwright-detail-<date>.json`. This run serves two purposes: (1) regression guard so fixes to the drawer do not accidentally regress the DetailPage, (2) ground-truth "what DB fields actually render somewhere today" that AU-7 can reuse when deciding drawer section order.
**Test Scenarios:**
- JHU C18050: passes for Inventors, Keywords, Development Stage, Advantages (as string via `stripHtml`), Publications, Full Description.
- A Flintbox university with `contacts` stored as dict array: passes if SidePanel renders contacts; malformed-contacts cases are logged, not promoted to fail.
- Record with null `raw_data`: minimal-page render; test passes with zero per-section assertions.
**Verification:**
`docs/qa/playwright-detail-<date>.json` exists. Zero crashes. Any missing sections are true gaps worth fixing on the DetailPage too (or worth relaxing in the catalog).

---

### AU-6: parseRawData shape-variant normalization
- [ ] **Goal:** Eliminate silent field drops by making `parseRawData` produce non-undefined output for every known shape variant, emitting both `*Html`/text and `*List`/array forms when the source can be either.
**Requirements:** R7, R11
**Dependencies:** AU-2 (hard — identifies which fields surface as `malformed`). Informed by AU-4 + AU-5 first runs (which confirm silent drops vs. unrendered-but-parsed) but does not block on them; AU-4/AU-5 may be rerun after AU-6 lands.
**Files:**
- `web/src/components/Detail/parseRawData.ts` — add `Array.isArray` guards and string↔array dual-output for: `inventors` (currently array-only), `key_points`, `flintbox_tags`, `client_departments`, `technology_validation`. Add newline-split fallback where scrapers emit newline-delimited strings. Preserve every existing field name; additive only.
- `web/src/components/Detail/parseRawData.test-shapes.md` — new; short inventory of observed shapes per field (output of AU-2's malformed list)
**Approach:**
Do not introduce a new field-name scheme. For each field that today does `Array.isArray(r?.x) ? ... : undefined`, add a sibling `xText` branch that captures the string form (and HTML form where applicable). Where existing fields already expose dual outputs (`applications`/`applicationsText`, `advantages`/`advantagesText`, `publicationsHtml`/`publicationsList`), extend the same pattern. Continue to strip HTML at render sites, not at parse time — preserves the `dangerouslySetInnerHTML` escape hatch. Leave `stripHtml` untouched. Assertions about the resulting shapes belong in AU-7 rendering, not here.
**Test Scenarios:**
- `r.inventors = "Alice, Bob, Carol"` (Flintbox legacy): `inventors` remains undefined; new `inventorsText = "Alice, Bob, Carol"` (rendered in AU-7).
- `r.inventors = ["Alice", "Bob"]`: `inventors` populated as today; `inventorsText` undefined.
- `r.key_points = "bullet1\nbullet2"`: new `keyPointsText` populated; `keyPoints` undefined.
- All existing callers of `parsed.inventors` (SidePanel, DiscoveryDrawer) continue to work unchanged.
**Verification:**
TypeScript compiles. `grep -r 'parsed\.' web/src/` surfaces no new undefined accesses. Running AU-4 tests against the JHU record shows no change in pass/fail yet (renderer changes come in AU-7) — but the parser's output now contains non-undefined branches for previously silent drops.

---

### AU-7: Extract shared section components; refactor DetailPage onto them
- [ ] **Goal:** Move every rendered block on DetailPage into `web/src/components/Detail/sections/` as per-section components with a uniform prop contract, and rebuild DetailPage on top of them without visual regression.
**Requirements:** R8
**Dependencies:** AU-6
**Files:**
- `web/src/components/Detail/sections/` — new folder; one component per UI section mirroring AU-2's catalog (e.g. `InventorsSection.tsx`, `DevelopmentStageSection.tsx`, `PublicationsSection.tsx`, `AdvantagesSection.tsx`, `KeywordsSection.tsx`, `DescriptionSection.tsx`, etc.). Each component branches internally on the available shape (`advantages` array vs `advantagesText` string, etc.) and returns `null` when empty.
- `web/src/pages/DetailPage.tsx` — reassemble the two-column layout by importing from `sections/`; preserve the current visual structure and the surrounding `ErrorBoundary` wrap.
- `web/src/components/Detail/ContentSections.tsx`, `SidePanel.tsx` — delete or reduce to thin re-export shells that forward to the new `sections/` tree.
**Approach:**
Uniform prop contract: `(parsed: ParsedRawData, tech: TechnologyDetail) => JSX.Element | null`. A section component never assumes layout; it renders its own heading and content, and lets the parent decide positioning. This makes the drawer consumer (AU-8) layout-independent. `AssessmentSection` stays on DetailPage as-is and is NOT extracted into `sections/` — it is explicitly out of scope for drawer parity (see Scope Boundaries). Do not re-order DetailPage visually; the refactor is structural only. Verify in-browser by loading JHU C18050 before and after and confirming visual identity.
**Test Scenarios:**
- DetailPage for JHU C18050 pre- vs. post-refactor: visually identical; all sections present in the same order.
- DetailPage for a Flintbox record (e.g. CMU): renders contacts, inventors, publications as before.
- Record with `raw_data = {}`: DetailPage shows title + minimal fields without crash; every section component returns null cleanly.
**Verification:**
AU-5 Playwright detail spec passes with the same per-record results it produced pre-refactor (rerun on same samples, diff should be empty). `grep ErrorBoundary web/src/pages/DetailPage.tsx` still matches — boundary preserved.

---

### AU-8: Drawer consumes shared sections + `?openTech=` deep link
- [ ] **Goal:** Replace `DrawerBody` with a `DrawerSections` tree that imports from `sections/`, rendering every drawer-surface section in a single-column drawer layout; add `?openTech=<uuid>` query-param hydration so the drawer can be opened by URL.
**Requirements:** R5, R8
**Dependencies:** AU-7
**Files:**
- `web/src/components/Discovery/DiscoveryDrawer.tsx` — replace the current inline `DrawerBody` block with a `DrawerSections` composition that imports from `web/src/components/Detail/sections/`. Preserve the drawer header, footer, and close/escape behavior.
- `web/src/pages/DiscoveryPage.tsx` — on mount and on URL change, read `?openTech=<uuid>`; if present, set `selectedUuid` to hydrate the drawer. Additive; does not alter existing click-to-open behavior.
- `web/src/components/Discovery/TechCard.tsx` — no functional change (the `data-uuid` attribute already added in AU-4 is retained).
**Approach:**
The drawer consumes the same section components DetailPage uses; layout differs. A drawer-scoped wrapper CSS class (`.drawer-sections`) targets single-column spacing/typography so section components remain layout-agnostic. Only sections listed with `surfaces: [..., "drawer"]` in the catalog (AU-2) are composed into `DrawerSections` — the catalog is still the single source of truth. `AssessmentSection` is excluded. The `?openTech=` hydration logic sets `selectedUuid` once when the query param is present; it does not round-trip back to URL unless the user explicitly bookmarks. The CLAUDE.md golden-path rule applies: before declaring the unit complete, verify in-browser for JHU C18050, a Flintbox record, and a record with minimal `raw_data`.
**Test Scenarios:**
- Drawer for JHU C18050: renders Description, Full Description, Background, Technical Problem, Advantages (via `advantagesText`), Inventors (5 items), Development Stage, Keywords, Publications, IP Status — every drawer-surface section DetailPage renders for this record.
- Navigate to `/?openTech=<uuid>` directly: drawer opens on mount with the target record loaded.
- Record with `raw_data = {}`: drawer shows only top-level description + "no other fields" quiet state; no blank panes.
- Assessment content is NOT rendered in the drawer (still DetailPage-only).
**Verification:**
AU-4 Playwright drawer spec rerun shows ≥98% per-section pass across all sampled records. No `UNREACHABLE` results (deep-link works). `grep ErrorBoundary web/src/components/Discovery/DiscoveryDrawer.tsx` OR its parent still matches — boundary preserved. Console shows zero `Array.isArray`/render errors for any sampled record.

---

### AU-9: Gap matrix generator + fix-loop orchestration
- [ ] **Goal:** Merge DB audit + Playwright drawer + Playwright detail outputs into a single per-university pass/fail matrix and a rerun orchestrator.
**Requirements:** R9, R11
**Dependencies:** AU-2, AU-4, AU-5
**Files:**
- `src/qa/matrix.py` — new; reads the three JSON outputs, emits `docs/qa/migration-matrix-<date>.md` and `.json`
- `src/cli.py` — register `migration-qa matrix` subcommand + `migration-qa run` umbrella that runs sample → audit-db → Playwright (via `subprocess.run` on `npm run test:e2e`) → matrix
- `docs/qa/README.md` — new; documents the artifact lifecycle (`samples-*.json`, `db-coverage-*.{md,json}`, `playwright-*.json`, `migration-matrix-*.md`), where to look when regressions appear, how to diff between dated artifacts
**Approach:**
Matrix rows are universities, columns are UI sections (from the catalog). Each cell shows `pass/fail/no-data/crash`, aggregated across the sampled records per cell — e.g. `12/15 pass, 3 no-data`. A separate "Surfaces" column pair shows drawer vs detail results side-by-side so drawer-only regressions are obvious. `migration-qa run` is synchronous, reports failures at each stage, and refuses to overwrite today's artifact (timestamp in filename). The rerun flow is `migration-qa run --fresh-samples` (re-samples) vs `migration-qa run --reuse-samples <path>` (same UUIDs, for before/after comparison during AU-6/AU-7/AU-8 iteration). The matrix is the single source of truth for "are we done?"
**Test Scenarios:**
- Run with all three inputs present: produces a matrix with one row per sampled university, one column pair (drawer | detail) per section. DetailPage columns pass; drawer columns reflect current AU-8 state.
- Rerun with `--reuse-samples`: diff against previous matrix shows only sections whose status changed; used to verify a parser/drawer fix closed exactly the intended gap without regressing others.
- Missing Playwright JSON (suite not yet run): `migration-qa matrix` exits non-zero with a clear error; `migration-qa run` runs the suite first.
**Verification:**
`docs/qa/migration-matrix-<date>.md` renders as a readable markdown table. Every sampled university appears. Before-AU-8 and after-AU-8 matrices diff cleanly (only drawer columns change). Summary footer shows total pass rate. Destructive-op check: `grep -rE '(UPDATE|INSERT|DELETE|session\.add|session\.merge|session\.delete)' src/qa/` returns zero matches — the audit pipeline is read-only by contract.

---

### AU-10: Production sign-off run + final matrix commit
- [ ] **Goal:** Run the full suite against the live Vercel URL, gated on deploy SHA matching `origin/Migration-QA` HEAD, and commit the final matrix artifact.
**Requirements:** R10, R11
**Dependencies:** AU-9, local matrix showing ≥98% pass on drawer+detail
**Files:**
- `src/qa/production_run.py` — new; resolves the expected SHA via `git rev-parse origin/Migration-QA`, fetches Vercel deployment metadata (commit SHA from the deployed HTML's `<meta>` or from the Vercel API if a token is available in env), refuses to proceed unless the deployed SHA matches, then invokes `PLAYWRIGHT_BASE_URL=https://web-one-lake-22.vercel.app npm run test:e2e`
- `src/cli.py` — register `migration-qa run --target prod`
- `docs/qa/migration-matrix-<date>-prod.md` — committed; the signed-off artifact
- `docs/qa/README.md` — extend with the "when to rerun" guidance
**Approach:**
The SHA comparand is `git rev-parse origin/Migration-QA` (the branch currently in flight). If the user has merged to main before this AU runs, the branch-head override can be passed via `--ref origin/main`. Vercel's rolling deploys can silently lag; if the SHA does not match, abort with a pointer to the Vercel dashboard and deploy status. When matched, run the same drawer + detail specs against `https://web-one-lake-22.vercel.app`. Expect some environment-driven flake (cold Railway starts, Vercel CDN warm-up); `retries: 2` in Playwright config absorbs. The prod-suffixed matrix is the shippable artifact; it lives under `docs/qa/` as a durable record. Nothing in this AU mutates code, scrapers, or DB.
**Test Scenarios:**
- SHA matches, suite passes at ≥98%: commit the matrix, mark the Migration-QA branch ready for merge.
- SHA mismatch: script aborts with "Vercel is serving <deployed_sha>; origin/Migration-QA is <head_sha>. Redeploy or wait, then re-run."
- Cold-start flake on Railway: first-pass retries succeed on second attempt; matrix reports `flaky` as distinct from `fail`.
**Verification:**
`docs/qa/migration-matrix-<date>-prod.md` committed. Pass rate visible in the summary footer. Any remaining per-university gaps are either (a) data-shape edge cases flagged for a future scraper run, or (b) non-section content variances (whitespace, HTML tag order) judged acceptable.

---

## Dependency Graph

```
AU-1 ──> AU-2 ─────────────────────────────┐
  │        │                                │
  │        ├──> AU-4 ──┐                    │
  │        └──> AU-5 ──┤                    ├──> AU-9 ──> AU-10
AU-3 ──────> AU-4/5 ───┤                    │
                       │                    │
                    AU-6 ──> AU-7 ──> AU-8 ─┘
```

- **AU-1** gates every audit/test that needs the sample list.
- **AU-2** is a hard dependency of AU-4, AU-5, and AU-6 (catalog + coverage JSON). AU-3 is independent infrastructure and can run in parallel with AU-1/AU-2.
- **AU-4 + AU-5** first runs are diagnostic; their output informs AU-6 scope but does not block AU-6.
- **AU-6** is a safe additive parser change. It precedes AU-7 because the new shape-variant outputs drive what the extracted section components branch on.
- **AU-7** extracts shared section components and keeps DetailPage visually unchanged; **AU-8** is where the drawer starts consuming those shared components + adds `?openTech=`. Splitting keeps each unit to ≤3 core files.
- **AU-9** is the reusable matrix/orchestrator — once built, re-running it is the fix loop for AU-6 → AU-8 iteration.
- **AU-10** is only sensible after AU-9 reports clean locally and Vercel serves the matching SHA.

## Key Technical Decisions

- **Drawer reaches parity via shared section components, not via embedding DetailPage in the drawer.** Preserves independent styling and avoids two-column-inside-a-drawer bugs. Cost: one-time refactor of `ContentSections` + `SidePanel` into a section folder.
- **Sampling is deterministic with a per-university seed.** Stable UUIDs across runs enable before/after matrix diffs — the primary regression signal in the fix loop.
- **Field unit is UI sections, not raw_data keys.** Matches user directive; keeps the matrix human-readable; defers silent-drop detection to the parser's own normalization (AU-6) rather than a TS-to-Python evaluator.
- **Playwright targets local-dev+prod-API for iteration, Vercel for sign-off.** Avoids Vercel lag during fix loops; prod SHA gate prevents false clean signals.
- **No CI integration in this plan.** The repo has no `.github/` today; adding CI is a separate concern. `migration-qa run` is the manual entry point; it is reproducible enough to serve as the gate.
- **`?openTech=<uuid>` as the drawer deep-link surface (AU-8).** Additive query param; doesn't change click behavior. AU-4's first runs use `data-uuid` card selectors (added in AU-4) as a deterministic opener that does not depend on the deep-link existing yet, so the spec runs diagnostically before AU-8 lands.
- **AU-7/AU-8 split.** Extract-from-DetailPage and consume-in-drawer are separate concerns with different review surfaces and different risks. Splitting keeps each unit to ≤3 core files and makes the drawer consumer change reviewable in isolation.
- **Catalog-first audit.** `src/qa/section_catalog.py` is the single source of truth for "what sections exist and which raw_data keys feed them." Both the Python auditor and the TypeScript renderer consume it conceptually; drift is caught by AU-4 (Playwright sees DOM ≠ catalog) rather than by shared runtime code.

## Open Questions

### Resolved During Planning
- **Drawer vs link-to-detail decision:** resolved — drawer reaches DetailPage parity via shared section components; `/technology/:uuid` remains as deep-link surface. `TechCard` keeps opening the drawer; no new link added from the card.
- **Assertion target:** resolved — every rendered UI section on DetailPage must be reachable from the drawer; verified per-sample via Playwright.
- **Test environment:** resolved — local dev + prod API for iteration, Vercel prod for sign-off, deploy SHA gated.
- **Fix scope for DB shape mismatches:** resolved — parser/renderer only; scraper code changes allowed but not triggered by this plan; no retroactive DB writes.
- **Audit baseline (live vs. original scraped raw_data):** resolved by default — live (post-correction) raw_data, since that is what users see. `QACorrection` original values are not consulted.
- **Stratification fallback when `development_stage` is absent:** resolved — oldest + newest + 13 random (deterministic seed), documented in AU-1.
- **Universities with <15 records:** resolved — sample `min(count, 15)`, mark `FULL_COVERAGE`, noted in summary (AU-1).
- **Drawer crash vs. missing field:** resolved — `assertDrawerAlive(page, tech)` checks for title presence before per-section assertions; absence reports `CRASH` distinct from `MISSING_FIELD` (AU-4 fixture).

### Deferred to Implementation
- Exact CSS scoping for drawer-column section styling may need tweaks per section when AU-7 reassembles DetailPage from the new folder. Resolve in-browser while building.
- Whether `?openTech=` should also update the browser URL when the drawer is opened via click (back-button semantics). Defer — minimal additive pattern first.
- Rate-limit posture against Railway when running 300+ Playwright navs in parallel. Measure during AU-4's first run; add `page.waitForTimeout(250)` or reduce workers only if 429s appear.
- Whether to add a `migration-qa diff` subcommand that auto-diffs two matrices. Nice-to-have once AU-8 lands.
- Which records to flag for eventual scraper follow-up — emerges as AU-6 leaves some fields in `malformed` state that cannot be safely coerced.

## Unchanged Invariants

- `GET /api/technologies/:uuid` response shape (every field in `TechnologyDetail`) must not change.
- `technologies` table DDL unchanged; no migrations.
- `/technology/:uuid` route continues to resolve, renders visually identical to pre-AU-7.
- The `/qa` review tool (`QASample`, `QACorrection`, `PATCH /api/technologies/:uuid/raw-data`) is not touched and remains functional.
- Assessment pipeline (`TechnologyAssessment`, `AssessmentSection`) rendering remains intact; the drawer may or may not render assessments — defer that decision.
- Existing React `ErrorBoundary` must stay in the tree; AU-7 must not unwrap it.
- No scraper is invoked by this plan (no Playwright calls to the server-side `/proxy` endpoint; no `scrape` CLI usage).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Drawer parity expands the drawer to an unusable height | Med | Med | AU-8 uses the same component primitives as DetailPage but in a single-column flow; user-test on 2-3 real records before locking styling. `AssessmentSection` is already formally out of scope for the drawer (Scope Boundaries). |
| Playwright 300-case run hammers Railway cold starts | Med | Low-Med | `retries: 2`, optional `page.waitForTimeout(250)`, `workers` cap at 4 in CI mode. Warmup ping in `globalSetup`. |
| `?openTech=` deep link interacts badly with existing search URL state | Low | Med | AU-8 hydrates selection once on mount; does not round-trip back to URL unless user requests it. Regression covered by AU-5 spec (DetailPage untouched) and by manual click-through test. |
| AU-6 parser normalization accidentally changes the shape of fields already rendered correctly (e.g. Stanford) | Med | High | Additive-only contract: new `*Text` / `*List` fields added; never mutate existing field names or shapes. AU-5 detail spec run pre- and post-AU-6 must show zero regressions. |
| AU-7 section extraction silently drops the `ErrorBoundary` wrap | Low | High | AU-7 and AU-8 verification steps explicitly grep for `ErrorBoundary` in the post-refactor tree. In-browser check: force a render error on one section and confirm the boundary catches it without blanking the entire page. |
| Sample stratification misses a university's dominant shape variant | Low | Med | Fallback to random fill within the 15 budget surfaces variance. If a rare shape only appears in record #47, AU-6 may miss it until a later sweep — acceptable risk, re-runs catch it. |
| Vercel deploy lags HEAD; AU-9 false clean signal | Low | High | Hard SHA gate in AU-9; aborts when mismatched. |
| Prod Playwright creates noisy analytics events on Vercel | Low | Low | Playwright runs have a distinct user agent; filter downstream if needed. |
| Shared section components introduce a cycle (Detail imports Drawer, Drawer imports Detail) | Low | Med | All sections live under `web/src/components/Detail/sections/`; both DetailPage and DiscoveryDrawer import from there; no reverse imports. |

## Sources & References

- **Research agents (this planning session):** repo-research-analyst, learnings-researcher, best-practices-researcher, spec-flow-analyzer. Findings inlined into Context Summary and AUs.
- `web/src/components/Detail/parseRawData.ts` — 46 parsed fields; current guard coverage documented in repo-research-analyst report.
- `web/src/components/Discovery/DiscoveryDrawer.tsx` — current ~10-field render surface.
- `web/src/pages/DetailPage.tsx` + `web/src/components/Detail/ContentSections.tsx` + `SidePanel.tsx` — parity target.
- `src/cli.py` + `src/database.py` — Click/Rich/Loguru + SQLAlchemy patterns for AU-1, AU-2, AU-8, AU-9.
- `src/scrapers/registry.py` — authoritative 37-university list.
- Commits `13da7ff`, `fd7b8f6`, `25359ff`, `876bfa3`, `d7a754e` — prior shape-variant fixes; inform AU-6 scope.
- Playwright 1.59 release notes; Playwright official docs on parallelism, best practices, web server.
- CLAUDE.md (project + global): no retroactive DB writes; verification-before-done discipline; `/learn` after this lands to seed `docs/solutions/ui-bugs/`.
- Memory: deployment URLs (Vercel `web-one-lake-22`, Railway `api-production-10c1`).

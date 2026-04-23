---
title: parseRawData silent field drops when scrapers emit variant shapes
category: ui-bugs
date: 2026-04-23
tags: [parseRawData, raw_data, scraper-normalization, silent-drop, Array.isArray, shape-variant, frontend, discovery-drawer, detail-page]
related-files:
  - web/src/components/Detail/parseRawData.ts
  - src/qa/section_catalog.py
  - src/qa/migration_audit.py
  - web/src/components/Detail/parseRawData.test-shapes.md
---

## Problem

The new Discovery drawer rendered "only the description" for the same records
the old full DetailPage rendered in rich detail (Inventors, Development Stage,
Keywords, Advantages, Publications). Surface symptom looked like a data-loss
regression. Initial instinct: the scraper or DB schema had dropped the rich
metadata.

Actual pattern: **`parseRawData` silently returned `undefined` for fields the
specific university's scraper had emitted in a non-expected shape.** JHU stores
`development_stage` as a string; UPenn and WayneState store it as a JSON
array. The parser's `r?.development_stage as string | undefined` cast returned
the string for JHU but the drawer renderer still skipped the Advantages
section (stored as `plain_string` not `array_of_strings`), and the audit
surfaced 18 malformed `development_stage` records across 35 universities.

## Investigation

- Direct DB query of JHU C18050 confirmed every field was present in
  `raw_data` (inventors=5 items, development_stage=29-char string, etc.).
  Data layer intact — confirmed this was not data loss.
- Read `parseRawData.ts` against actual DB shapes: found that only
  `applications`, `advantages`, `publications`, and `researchers` had
  Array.isArray guards with string fallbacks. Every other field (`inventors`,
  `key_points`, `flintbox_tags`, `client_departments`,
  `technology_validation`, `development_stage`) blind-cast to the expected
  type — when the scraper shipped a different shape, the field silently
  became undefined.
- Cross-checked `DiscoveryDrawer.tsx`: even when `parseRawData` exposed a
  `*Text` fallback (like `advantagesText`), the drawer only rendered the
  array form (`parsed.advantages`) — so string-form data was silently
  dropped in the render layer, separate from the parse layer.
- Built a catalog-driven audit (`src/qa/migration_audit.py`) that classifies
  each field's shape against a closed token set
  (`array_of_strings`, `plain_string`, `newline_string`, `html_string`,
  `array_of_objects`, `comma_string`, `object`). Running it across 525
  sampled records surfaced the 18 malformed cells — all Development Stage —
  concentrated in UPenn and WayneState.

## Root Cause

Three compounding factors:

1. **Scraper-level shape drift.** The same field name means different things
   across scrapers: `development_stage` is a `plain_string` for JHU but an
   `array_of_strings` for UPenn/WayneState. This is legitimate — some TTOs
   structure stage as a bullet list, others as a paragraph. The DB is
   shape-pluralistic by design (`raw_data` is `JSONB`).

2. **Unguarded casts in the parser.** TypeScript's `as string | undefined`
   assertion is a lie at runtime. The cast compiles but returns whatever was
   actually in `raw_data`. When that's an array, downstream `.map()` / string
   ops either crash React (pre-ErrorBoundary) or simply don't render
   anything (post-ErrorBoundary).

3. **Drawer renderer only consumed the array branch.** Even fields with
   dual-output in the parser (`advantages` / `advantagesText`) had renderers
   that only checked the array form. The `*Text` fallback existed in the
   parser but was never consumed.

## Solution

Three coordinated changes:

1. **`parseRawData.ts` dual-output helpers.** Every field that can arrive as
   string or array now emits both a `<field>` (array if array, else
   undefined) and a `<field>Text` (string if string, or joined from array):

   ```ts
   function asArrayOrText(value: unknown): { array?: string[]; text?: string } {
     if (Array.isArray(value)) {
       const strings = value.filter((x): x is string => typeof x === 'string' && x.trim())
       return { array: strings }
     }
     if (typeof value === 'string' && value.trim()) return { text: value }
     return {}
   }
   ```

   Applied to `inventors`, `key_points`, `applications`, `advantages`,
   `flintbox_tags`, `client_departments`, `technology_validation`.

2. **`stringOrList` for fields that SHOULD be strings.** `development_stage`
   renders inline as a single paragraph; when scrapers emit an array, the
   parser joins with `\n` and exposes both `developmentStage` (joined) and
   `developmentStageList` (array) for renderers that want bullets:

   ```ts
   function stringOrList(value: unknown): { text?: string; list?: string[] } {
     if (typeof value === 'string' && value.trim()) return { text: value }
     if (Array.isArray(value)) {
       const strings = value.filter((x): x is string => typeof x === 'string' && x.trim())
       if (strings.length) return { text: strings.join('\n'), list: strings }
     }
     return {}
   }
   ```

3. **Shared section components consume both branches.** Each section
   component in `web/src/components/Detail/sections/content.tsx` checks the
   array form first, then falls back to the text form:

   ```tsx
   export function InventorsSection({ data }: SectionProps) {
     if (data.inventors?.length) return <PillList items={data.inventors} />
     if (data.inventorsText) return <TextSection text={data.inventorsText} />
     return null
   }
   ```

Final state after AU-6 + AU-7 + AU-8: 0 malformed cells across 525 records,
drawer and detail 100% section-visibility parity for every record that has
data.

## Prevention

- [ ] **Never `as` cast from `raw_data`.** Every read of `raw_data[key]`
      must use `Array.isArray`, `typeof === 'string'`, or `typeof === 'object'`
      guards. The parser is a boundary; treat it like user input.
- [ ] **Dual-output for every field that can be string-or-array.** The default
      pattern is `<field>` + `<field>Text`. Renderers that care about only one
      branch still must check both — null-safe.
- [ ] **Audit surface sections, not raw_data keys.** The question "did this
      render for the user?" is about UI sections (≈30), not `raw_data` keys
      (50+ across scrapers). A catalog that maps sections → accepted shapes
      is the right unit.
- [ ] **Treat `malformed` as a parser-bug signal, not a data-bug signal.**
      When the DB auditor reports malformed, the fix is either (a) add the
      observed shape to the catalog's accepted list, or (b) extend
      `parseRawData` to normalize the shape into an accepted one. Do not
      re-scrape or mutate DB records (CLAUDE.md R11 invariant).
- [ ] **Share section components across surfaces.** Drawer and DetailPage
      should import the same per-section components so a parser fix
      automatically benefits both surfaces. See
      `web/src/components/Detail/sections/`.

## See also

- Commit `13da7ff` — the original Flintbox `.map()`-on-string crash fix that
  introduced `Array.isArray` guards + `ErrorBoundary`. Patterns here extend
  that work instead of replacing it.
- Commit `fd7b8f6` — CMU Flintbox contact/publications flattening. Same
  failure mode in a different field.
- Commit `25359ff` — canonical field-name standardization across 11 scrapers.
  The parser still handles legacy keys but the canonical ones are preferred.

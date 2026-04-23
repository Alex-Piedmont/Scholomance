---
title: Playwright alive-check via escape+slice regex needle misreads titles with special characters
category: test-failures
date: 2026-04-23
tags: [playwright, e2e, regex, crash-detection, alive-check, special-characters, escape, CRASH-vs-MISSING]
related-files:
  - web/e2e/fixtures/crash-detection.ts
  - web/e2e/drawer-parity.spec.ts
  - web/e2e/detail-page.spec.ts
---

## Problem

The drawer parity spec used a utility to distinguish "drawer crashed
(blank body)" from "drawer rendered but sections are missing":

```ts
export async function assertSurfaceAlive(scope: Locator, title: string) {
  const needle = title.trim().slice(0, 60)
  await scope.getByText(new RegExp(escapeRegex(needle).slice(0, 60), 'i')).first().waitFor({
    state: 'visible', timeout: 10_000,
  })
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
```

In a full 1050-test sweep, 5 records reported `CRASH` that, when run in
isolation, passed cleanly. Common pattern in the failing titles:

- `'2019-041,  hNQO1 Activatable Fluorescent Probe'` (comma + double space)
- `'Difficult Decisions in Pediatric Care:  Just Because We Can,'`
  (colon + double space + trailing comma)
- `'"Smart" Glucose-Responsive  Insulin'` (curly quotes)
- `'(SD2023-060)   Penalized Reference Matching algorithm'` (triple space)

The drawer DOM contained the correct title in `.drawer__title`. Sections
rendered correctly (the full detail spec passed all 5). The alive-check
alone mis-classified them.

## Investigation

- Ran each of the 5 records individually — all passed. Confirmed not a
  scraper or React rendering bug.
- Traced the alive helper: `escapeRegex(needle).slice(0, 60)`. The escape
  runs first (length can grow by up to 2x for each escaped char), then the
  slice to 60 chars. For a title containing backslashes or complex
  punctuation, the slice can cut mid-escape-sequence and produce an
  invalid or semantically-wrong regex.
- Additionally, the needle is matched with `getByText` which uses the
  accessible-text tree. Leading/trailing whitespace normalization differs
  between source text and rendered text; a needle that includes leading
  whitespace may not match even when the visible text is identical.
- Crucially: **this was a flake-inducing pattern** — the test "flaked"
  precisely because the source text for some records was unusual but valid,
  not because of timing.

## Root Cause

Building a regex from a content string is fragile. The combination of:

1. **Escape-then-slice ordering** — slicing after escape can truncate in
   the middle of a `\\.` sequence, producing an orphan backslash.
2. **Content-coupled regex** — any title containing newlines, curly
   quotes, or non-BMP Unicode can be classified differently by the
   accessible-name tree than by the source string.
3. **Over-engineering the "alive" signal** — the goal was just "did the
   surface render at all?" but we tied the signal to a specific string
   match.

A crash-vs-missing classifier should use a structural DOM signal, not a
content-matched regex.

## Solution

Replace the regex-based alive check with a direct element presence check
on a known DOM landmark:

```ts
let titleText = ''
let aliveStatus: AliveStatus = 'crash'
try {
  await drawer.locator('.drawer__title').waitFor({ state: 'visible', timeout: 8_000 })
  titleText = (await drawer.locator('.drawer__title').innerText().catch(() => '')) || ''
  if (titleText.trim().length > 0) aliveStatus = 'alive'
} catch {
  /* leaves aliveStatus = 'crash' */
}
```

Equivalent for DetailPage uses `h1` as the landmark. Both now check:
"Does the DOM landmark element exist, is it visible, and does it have
non-empty text?" That's a structural question with no content coupling.

After the fix, all 5 previously-"crashing" records pass cleanly in the
full sweep: Drawer 4780/4780 (100%), Detail 4778/4780 (99.96% —
2 cold-start flakes self-heal on rerun with `retries: 2`).

## Prevention

- [ ] **Never build a regex from user-controlled content.** If you must
      match content, prefer literal substring matching (`.toContain()`,
      `page.getByText(literalString, { exact: false })`) over regex.
- [ ] **Alive-checks should be structural.** Ask "does landmark X exist?",
      not "does landmark X contain content matching Y?".
- [ ] **If you escape AND slice, slice the pre-escape input, then escape.**
      `escapeRegex(content.slice(0, 60))` is safe; `escapeRegex(content).slice(0, 60)`
      is not.
- [ ] **Test your crash detector with edge-case strings.** Seed a record
      with a title containing curly quotes, double spaces, trailing
      punctuation, and non-BMP characters; confirm the alive check still
      returns `alive`.
- [ ] **Distinguish flake from real crash by running failing tests
      individually.** A test that fails in the sweep and passes solo is
      almost always an infra-harness bug, not a product bug.

## See also

- Commit `84e9f6b` — the alive-check fix (replaces regex with
  `.drawer__title` landmark + `innerText`).
- Playwright docs on [auto-retrying assertions](https://playwright.dev/docs/test-assertions#auto-retrying-assertions)
  — `waitFor` with `state: 'visible'` is the idiomatic alive check.

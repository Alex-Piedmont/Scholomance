---
title: Playwright expect.soft() never throws — wraps all assertions in try/catch uselessly
category: test-failures
date: 2026-04-23
tags: [playwright, e2e, expect, expect.soft, try-catch, test-assertion, flaky-pattern]
related-files:
  - web/e2e/drawer-parity.spec.ts
  - web/e2e/detail-page.spec.ts
---

## Problem

Per-section assertions in the Migration-QA drawer/detail specs looked like
this, with the goal of testing every expected section without
short-circuiting at the first failure:

```ts
for (const sid of expectedSections) {
  const loc = SECTION_SELECTORS[sid](drawer)
  try {
    await expect.soft(loc.first()).toBeVisible({ timeout: 2_000 })
    sections.push({ sectionId: sid, status: 'pass' })
  } catch {
    sections.push({ sectionId: sid, status: 'missing' })
    anyMissing = true
  }
}
```

The JSON output reported every section as `pass` — even for records where
Playwright's HTML report clearly showed missing assertions. The test-level
status was computed from `anyMissing` which was always `false`, yet the
tests themselves were marked failed in the Playwright summary. The two
signals disagreed.

## Investigation

Ran a single JHU detail test in isolation: JSON said 15 sections passed, but
Playwright's `--reporter=list` output showed the test failed. Checked the
Playwright HTML report: each soft-expect failure was recorded but the test
continued executing.

Re-read Playwright docs: **`expect.soft(...)` deliberately does NOT throw
on failure.** It records the failure for the test-level aggregation and
keeps executing. The `try/catch` around it never fires. Hard `expect(...)`
throws; `expect.soft(...)` does not.

## Root Cause

`expect.soft` is designed for a different use case: "I want to check many
things and see ALL the failures in the report, without stopping at the
first one." It's the opposite of what the try/catch pattern assumes.

The try/catch here was trying to reinvent soft-assert semantics (collect
per-section results) but combined with soft-expect, it made the catch
branch unreachable — everything was reported as pass regardless of actual
visibility.

## Solution

Use **hard** `expect(...)` inside the per-section try/catch (throws on
failure, catch branch fires), then emit a single `expect.soft` at the test
level with the accumulated missing list so the HTML report mirrors the JSON:

```ts
for (const sid of expectedSections) {
  const loc = SECTION_SELECTORS[sid](drawer)
  try {
    await expect(loc.first()).toBeVisible({ timeout: 2_000 })  // hard expect
    sections.push({ sectionId: sid, status: 'pass' })
  } catch {
    sections.push({ sectionId: sid, status: 'missing' })
    anyMissing = true
  }
}

if (anyMissing) {
  const missed = sections.filter(s => s.status === 'missing').map(s => s.sectionId)
  expect
    .soft(missed, `Drawer missing sections for ${uuid}: ${missed.join(', ')}`)
    .toEqual([])
}
```

Behavior after fix:
- Each section's per-record outcome is accurately captured in the JSON
  reporter (for the gap matrix).
- The Playwright HTML report shows one soft-expect failure per record with
  the list of missing sections — human-friendly debugging.
- The test-level pass/fail status agrees with the JSON status.

## Prevention

- [ ] **Mental model:** `expect(...)` = hard = throws. `expect.soft(...)` =
      recorded-but-non-throwing. Only hard expect interacts with try/catch.
- [ ] **If you want per-iteration handling, use hard expect + catch.** Soft
      expect is for aggregating failures into a single report, not for
      controlling flow.
- [ ] **Test your test harness.** Before running 1000+ data-driven cases,
      run 1 known-failing case through the harness and confirm the JSON
      reporter shape matches the HTML reporter's outcome.
- [ ] **When assertions control downstream logic (matrix computation,
      artifact writing), you cannot silently swallow them via soft expect.**
      Hard expect + catch + accumulate + one-summary-soft-expect is the
      Playwright idiom for this.

## See also

- Playwright docs on [soft assertions](https://playwright.dev/docs/test-assertions#soft-assertions).
- Commit `78ea81d` introduced the hard-expect + summary-soft-expect pattern
  in both `drawer-parity.spec.ts` and `detail-page.spec.ts`.

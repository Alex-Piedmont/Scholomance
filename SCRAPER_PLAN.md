# Scraper Review & Fix Plan

Tracking approval status for all scrapers. Each must be visually verified at `localhost:5173` before marking approved.

---

## Status Legend
- **Approved** — Visually verified by user, no issues
- **Needs Fix** — Issues identified, fix in progress or pending
- **Unreviewed** — Not yet checked by user

---

## Flintbox Base Scrapers (extend `FlintboxScraper`)
Inherit from `flintbox_base.py` — fixes to base class apply automatically.

| # | Code | University | Status | Notes |
|---|------|-----------|--------|-------|
| 1 | `usu` | Utah State | **Approved** | Phase 3 fix: metadata filtered from `other` |
| 2 | `uconn` | UConn | **Needs Fix** | `&nbsp;` in Market Opportunity; missing bullets in Market Application |
| 3 | `ttu` | Texas Tech | **Needs Fix** | Section parsing works on page 1; user flagged "still needs work" |
| 4 | `ucf` | Central Florida | **Approved** | |
| 5 | `colorado` | Colorado | **Approved** | |
| 6 | `usc` | South Carolina | **Approved** | |
| 7 | `louisville` | Louisville | **Approved** | |
| 8 | `iowa` | Iowa | **Approved** | |

## Flintbox Standalone Scrapers (own `_parse_api_item_with_detail`)
Import helpers from `flintbox_base.py` but have their own implementation.

| # | Code | University | Status | Notes |
|---|------|-----------|--------|-------|
| 9 | `gatech` | Georgia Tech | **Approved** | |
| 10 | `cmu` | Carnegie Mellon | **Needs Fix** | User asked about "Granted" — confirmed correct `ipStatus` data; needs user re-check |
| 11 | `cornell` | Cornell | **Needs Fix** | Section parsing added for Cornell headers; needs user re-verification |
| 12 | `uiuc` | UIUC | **Approved** | |
| 13 | `uga` | UGA | **Approved** | |

## TechPublisher Scrapers (extend `TechPublisherScraper`)

| # | Code | University | Status | Notes |
|---|------|-----------|--------|-------|
| 14 | `warf` | Wisconsin (WARF) | Unreviewed | |
| 15 | `uw` | Washington | Unreviewed | |
| 16 | `minnesota` | Minnesota | Unreviewed | |
| 17 | `purdue` | Purdue | **Approved** | Phase 2 fix: section parsing + inventor splitting |
| 18 | `umich` | Michigan | Unreviewed | |

## Algolia API Scrapers

| # | Code | University | Status | Notes |
|---|------|-----------|--------|-------|
| 19 | `northwestern` | Northwestern | **Approved** | |
| 20 | `unlv` | UNLV | **Approved** | |
| 21 | `waynestate` | Wayne State | Unreviewed | |
| 22 | `jhu` | Johns Hopkins | Unreviewed | Multi-category querying |
| 23 | `buffalo` | Buffalo | Unreviewed | |
| 24 | `uf` | Florida | Unreviewed | |

## RSS Feed Scrapers

| # | Code | University | Status | Notes |
|---|------|-----------|--------|-------|
| 25 | `princeton` | Princeton | Unreviewed | |
| 26 | `michiganstate` | Michigan State | Unreviewed | |
| 27 | `texasstate` | Texas State | Unreviewed | |
| 28 | `upenn` | Penn | Unreviewed | |
| 29 | `utaustin` | UT Austin | Unreviewed | |

## Custom Scrapers

| # | Code | University | Status | Notes |
|---|------|-----------|--------|-------|
| 30 | `ucsystem` | UC System | Unreviewed | Sitemap-based, centralized portal |
| 31 | `mit` | MIT | Unreviewed | Custom HTML scraper with patent extraction |
| 32 | `columbia` | **Approved** | Sitemap-based; added detail page fetching + structured section parsing |
| 33 | `stanford` | Stanford | Unreviewed | Playwright-based |
| 34 | `duke` | Duke | Unreviewed | Playwright-based with anti-bot measures |
| 35 | `harvard` | Harvard | Unreviewed | Category-based |

---

## Summary

| Category | Total | Approved | Needs Fix | Unreviewed |
|----------|-------|----------|-----------|------------|
| Flintbox Base | 8 | 6 | 2 | 0 |
| Flintbox Standalone | 5 | 3 | 2 | 0 |
| TechPublisher | 5 | 1 | 0 | 4 |
| Algolia API | 6 | 2 | 0 | 4 |
| RSS Feed | 5 | 0 | 0 | 5 |
| Custom | 6 | 1 | 0 | 5 |
| **Total** | **35** | **13** | **4** | **18** |

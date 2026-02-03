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

| # | Code | University | Status |
|---|------|-----------|--------|
| 1 | `usu` | Utah State | **Approved** |
| 2 | `uconn` | UConn | **Needs Fix** |
| 3 | `ttu` | Texas Tech | **Approved** |
| 4 | `ucf` | Central Florida | **Approved** |
| 5 | `colorado` | Colorado | **Approved** |
| 6 | `usc` | South Carolina | **Approved** |
| 7 | `louisville` | Louisville | **Approved** |
| 8 | `iowa` | Iowa | **Approved** |

## Flintbox Standalone Scrapers (own `_parse_api_item_with_detail`)
Import helpers from `flintbox_base.py` but have their own implementation.

| # | Code | University | Status |
|---|------|-----------|--------|
| 9 | `gatech` | Georgia Tech | **Approved** |
| 10 | `cmu` | Carnegie Mellon | **Needs Fix** |
| 11 | `cornell` | Cornell | **Approved** |
| 12 | `uiuc` | UIUC | **Approved** |
| 13 | `uga` | UGA | **Approved** |

## TechPublisher Scrapers (extend `TechPublisherScraper`)

| # | Code | University | Status |
|---|------|-----------|--------|
| 14 | `warf` | Wisconsin (WARF) | **Approved** |
| 15 | `uw` | Washington | Unreviewed |
| 16 | `minnesota` | Minnesota | Unreviewed |
| 17 | `purdue` | Purdue | **Approved** |
| 18 | `umich` | Michigan | Unreviewed |

## Algolia API Scrapers

| # | Code | University | Status |
|---|------|-----------|--------|
| 19 | `northwestern` | Northwestern | **Approved** |
| 20 | `unlv` | UNLV | **Approved** |
| 21 | `waynestate` | Wayne State | Unreviewed |
| 22 | `jhu` | Johns Hopkins | Unreviewed |
| 23 | `buffalo` | Buffalo | Unreviewed |
| 24 | `uf` | Florida | Unreviewed |

## RSS Feed Scrapers

| # | Code | University | Status |
|---|------|-----------|--------|
| 25 | `princeton` | Princeton | Unreviewed |
| 26 | `michiganstate` | Michigan State | **Approved** |
| 27 | `texasstate` | Texas State | Unreviewed |
| 28 | `upenn` | Penn | Unreviewed |
| 29 | `utaustin` | UT Austin | Unreviewed |

## Custom Scrapers

| # | Code | University | Status |
|---|------|-----------|--------|
| 30 | `ucsystem` | UC System | Unreviewed |
| 31 | `mit` | MIT | Unreviewed |
| 32 | `columbia` | Columbia | **Approved** |
| 33 | `stanford` | Stanford | Unreviewed |
| 34 | `duke` | Duke | Unreviewed |
| 35 | `harvard` | Harvard | Unreviewed |

---

## Summary

| Category | Total | Approved | Needs Fix | Unreviewed |
|----------|-------|----------|-----------|------------|
| Flintbox Base | 8 | 7 | 1 | 0 |
| Flintbox Standalone | 5 | 4 | 1 | 0 |
| TechPublisher | 5 | 2 | 0 | 3 |
| Algolia API | 6 | 2 | 0 | 4 |
| RSS Feed | 5 | 1 | 0 | 4 |
| Custom | 6 | 1 | 0 | 5 |
| **Total** | **35** | **17** | **2** | **16** |

---

## Follow-up Actions

| University | Action Needed |
|-----------|---------------|
| `ttu` | Full re-scrape needed (embedded section parsing applied to ~100/323 techs) |
| `cornell` | Full re-scrape needed (section parsing applied to ~298/1114 techs) |
| `michiganstate` | Full re-scrape needed (detail parser applied to ~15/340 techs) |
| `columbia` | Full re-scrape needed (detail fetching applied to ~15/1211 techs) |
| `uconn` | Fix `&nbsp;` in Market Opportunity; missing bullets in Market Application; re-scrape |
| `cmu` | User re-check needed; "Granted" ipStatus confirmed correct in data |

---

## Error / Solution Log

| University | Problem | Solution |
|-----------|---------|----------|
| `usu` | Metadata strings (IP status, dev stage) leaking into `other` field | Added `_is_metadata()` filter in `flintbox_base.py` |
| `ttu` | Raw HTML (`<br>`, `·&nbsp;`) in `market_application`/`benefit`; embedded sections (IP, dev stage, keywords) not parsed | Extended `_parse_embedded_sections()` for all section types; added BeautifulSoup HTML cleaning in `flintbox_base.py` |
| `cornell` | Abstract and Technology Overview merged; Publications/Patents absent; no HTML cleaning | Separated background/overview in `_parse_embedded_sections()`; added publications fallback from `publications_html`; duplicated HTML cleaning loop in `cornell.py` |
| `warf` | All content in `full_description` with markdown bold headers; authors not parsed from nested divs; Included IP not separated | Rewrote detail parser: invention/overview→`abstract`, applications/advantages→arrays, Included IP→`ip_text`; fixed author parsing for `div > div` structure |
| `michiganstate` | `&nbsp;` in description; detail page content not structured into sections | Rewrote detail parser with `<p>` heading detection for known section names; added `subtitle` for Executive Summary; added keyword parsing from "Key Words" section |
| `columbia` | `description=None` despite having page content; no detail page fetching | Added `_fetch_detail()` with concurrency; built section parser mapping h2 headings to standard raw_data field names |
| `purdue` | Sections not parsed; inventors concatenated | Added section parsing + inventor splitting |

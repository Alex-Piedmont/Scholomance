# Scraper Error/Solution Log
Errors encountered during scraper enrichment and their solutions.
---

## Phase 1a: FlintboxScraper base class (2026-02-02)

### Issue 1: Top-level Technology fields not populated
**Scrapers affected:** All 11 Flintbox scrapers (ucf, colorado, usc, usu, ttu, uconn, louisville, iowa, gatech, cmu, uiuc) + cornell
**Symptom:** `innovators`, `keywords`, `patent_status` always null despite detail data existing in `raw_data`
**Root cause:** `FlintboxScraper._parse_api_item_with_detail()` populated `raw_data` with detail fields but never passed `innovators`, `keywords`, or `patent_status` to the `Technology()` constructor.
**Solution:** Added field mapping after building `raw_data`:
- `innovators` from `detail['_members']` (extract `name` from each dict)
- `keywords` from `detail['_tags']` (list of strings)
- `patent_status` from `detail.get('ipStatus')`
**File:** `src/scrapers/flintbox_base.py`

### Issue 2: Poor description using 'other' field instead of 'abstract'
**Symptom:** Description showed "Invention Track Code: 11082 IP Track Code: 34020" instead of actual technology content
**Root cause:** Description logic prioritized the `other` field (which contains internal track codes) over the `abstract` field
**Solution:** Changed description priority to: `abstract` > `other` > `benefit` > key_points. All fields HTML-stripped with minimum length check (>20 chars) to skip empty/trivial content.
**File:** `src/scrapers/flintbox_base.py`

### Issue 3: Patent number and URL not visible in frontend
**Symptom:** `ip_number` (e.g., US10916918B2) and `ip_url` (Google Patents link) were stored in `raw_data` but not displayed on the detail page
**Root cause:** Frontend `DetailPage.tsx` only rendered `ip_status` text, not the patent number or link
**Solution:** Added `ipNumber` and `ipUrl` extraction from `raw_data`, rendered patent number as clickable link under the IP Status heading.
**File:** `web/src/pages/DetailPage.tsx`

### Issue 4: Stale data in DB after scraper fix
**Symptom:** After fixing the scraper, previously-scraped technologies still showed old data (missing fields)
**Root cause:** Technologies scraped before the fix retained their old `raw_data`. The fix only applies when technologies are re-scraped.
**Solution:** Re-scrape affected universities with sufficient page limit to cover all technologies. Data updates on re-scrape via upsert.

### Note: Standalone Flintbox scrapers (gatech, cmu, uiuc, cornell)
These scrapers have their own copy of `_parse_api_item_with_detail()` rather than inheriting from `FlintboxScraper`. They have the **same issues** and need the same fix applied individually. Pending Phase 1b/1c.

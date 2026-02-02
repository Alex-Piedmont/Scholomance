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
These scrapers have their own copy of `_parse_api_item_with_detail()` rather than inheriting from `FlintboxScraper`. They have the **same issues** and need the same fix applied individually. ~~Pending Phase 1b/1c.~~ **Fixed in Phase 1b/1c.**

## Phase 1b/1c: Standalone Flintbox scrapers (2026-02-02)

### Issue 5: Same bugs in gatech, cmu, uiuc, cornell, uga
**Scrapers affected:** gatech, cmu, uiuc, cornell, uga
**Symptom:** Identical to Issues 1 and 2 — no innovators/keywords/patent_status, description using `other` instead of `abstract`
**Root cause:** Each scraper had its own copy of `_parse_api_item_with_detail()` with the same bugs as the base class
**Solution:** Applied same fix to each file: description priority `abstract` > `other` > `benefit`, and field mapping for `innovators`, `keywords`, `patent_status` before `Technology()` constructor.
**Files:** `src/scrapers/gatech.py`, `src/scrapers/cmu.py`, `src/scrapers/uiuc.py`, `src/scrapers/cornell.py`, `src/scrapers/uga.py`

## Phase 2: TechPublisher scrapers (2026-02-02)

### Issue 6: Purdue description contains all sections in one blob
**Scrapers affected:** purdue
**Symptom:** Advantages, Applications, TRL, IP, and Keywords all lumped under "Description" header. No structured sections extracted.
**Root cause:** Purdue's `.description` div contains all content as flat `<p>` tags with bold labels (e.g., `<b>Advantages</b>:`) rather than separate HTML headings. The scraper grabbed the whole div as `full_description` without parsing internal sections.
**Solution:** Added `_parse_description_div()` method that walks `<p>` children, detects bold-label section headers, and splits content into `advantages`, `applications`, `trl`, `ip_text`, `keywords`, and `technology_validation` fields.
**File:** `src/scrapers/purdue.py`

### Issue 7: Purdue inventors not split into separate names
**Symptom:** Inventors stored as single string with `\n\n\n` separators (e.g., `['Name1\n\n\nName2']`) instead of separate list items
**Root cause:** Purdue's author collapsible body uses nested `<div><div>Name</div></div>` — no `<a>` or `<span>` tags. The parser fell through to comma-split fallback which concatenated names.
**Solution:** Added `div > div` selector before the `a, span` fallback to handle Purdue's nested div structure.
**File:** `src/scrapers/purdue.py`

### Issue 8: Supporting documents not linked, TRL/IP/validation not rendered
**Symptom:** Frontend missing TRL, Technology Validation, IP filing details, and supporting document links for TechPublisher scrapers
**Root cause:** `DetailPage.tsx` only rendered Flintbox-specific fields (`documents`, `ip_status`) and didn't handle TechPublisher fields (`supporting_documents`, `trl`, `ip_text`, `technology_validation`, `contact`)
**Solution:** Added frontend extraction and rendering for: `trl` and `technology_number` in subheader, `subtitle` below title, `technology_validation` as bulleted section, `ip_text` under IP Status, `supporting_documents` as linked downloads in sidebar, `contact` in sidebar.
**File:** `web/src/pages/DetailPage.tsx`

### Note: Other TechPublisher scrapers (uw, minnesota, princeton, michiganstate, texasstate)
These already have full BeautifulSoup detail parsing matching WARF's pattern. Verified working — descriptions, inventors, categories, patent tables all extracted. May need Purdue-style `_parse_description_div()` if their sites use the same flat `<p>` structure (to be verified).

## Phase 3: Flintbox display quality fixes — USU, UCONN, TTU (2026-02-02)

### Issue 9: USU "Overview" shows metadata instead of content
**Scrapers affected:** usu, uconn
**Symptom:** The `other` field contained internal metadata (ref numbers, inventor lists, contact info, "Case Manager Contact Information") rather than narrative content. Frontend rendered this under "Overview" via `otherHtml`.
**Root cause:** Flintbox API returns metadata in the `other` field for some universities. No quality check before storing it.
**Solution:** Added `_is_metadata()` helper that detects contact/ref metadata patterns ("Contact:", "Inventors:", "Case Manager", "USU Ref.", "Case Number", "Technology Category"). When `other` matches, it's stored as `raw_data["other_metadata"]` instead of `raw_data["other"]`, preventing frontend display. Same check skips metadata `other` when building the description.
**File:** `src/scrapers/flintbox_base.py`

### Issue 10: UCONN `·&nbsp;` formatting artifacts in display
**Scrapers affected:** All Flintbox scrapers (visible on uconn)
**Symptom:** Market application and other fields displayed `·&nbsp;&nbsp;&nbsp;` bullet formatting instead of clean text. HTML entities persisted after tag stripping.
**Root cause:** The HTML strip regex (`<[^>]+>`) removed tags but not HTML entities like `&nbsp;`, `&amp;`, `·`.
**Solution:** Two fixes:
1. Added `_clean_html_text()` helper in scraper that strips tags AND decodes entities (`&nbsp;`→space, `&amp;`→`&`, `·`/`•`→`- `). Used for description building.
2. Enhanced frontend `stripHtml()` in `parseRawData.ts` to also decode `&nbsp;`, `&amp;`, `&lt;`, `&gt;`, `&quot;` and convert `·`/`•` bullets to `- `. This fixes display for all raw_data HTML fields without re-scraping.
**Files:** `src/scrapers/flintbox_base.py`, `web/src/components/Detail/parseRawData.ts`

### Issue 11: TTU abstract contains embedded sections as single block
**Scrapers affected:** ttu (and potentially other Flintbox scrapers with similar API data)
**Symptom:** TTU's `abstract` field contained the full page content including "Market Applications:", "Features, Benefits & Advantages:", "Intellectual Property:", "Development Stage:", "Researchers:", "Keywords:" sections as HTML. Everything displayed as one text blob under "Abstract".
**Root cause:** Flintbox API returns all content in the `abstract` field for TTU, rather than using separate API fields like `marketApplication` and `benefit`.
**Solution:** Added `_parse_embedded_sections()` helper that detects and splits section markers (wrapped in `<p>`, `<strong>`, etc.) into structured fields. Extracts `market_application`, `benefit`, and `reference_number` from the abstract HTML, leaving only the actual abstract text. Only triggers when section markers are present (no impact on other universities). Parsed fields populate `raw_data` only when the API's own fields are empty.
**File:** `src/scrapers/flintbox_base.py`

#!/bin/bash
# fix_scrapers.sh - Enrich all scrapers with proper detail page data mapping
# Run from project root: bash fix_scrapers.sh
#
# Core issue: Most scrapers fetch detail data into raw_data but don't populate
# the top-level Technology fields (innovators, keywords, patent_status, description).
#
# Two phases:
# Phase 1: Fix base classes (flintbox_base.py, techpub_base.py) to properly map fields
# Phase 2: Fix individual scrapers that have stubs or unwired detail parsing

set -e

ERROR_LOG="SCRAPER_ERRORS.md"

if [ ! -f "$ERROR_LOG" ]; then
  cat > "$ERROR_LOG" << 'LOGEOF'
# Scraper Error/Solution Log
Errors encountered during scraper enrichment and their solutions.
---
LOGEOF
fi

echo "============================================"
echo "Scraper Enrichment Script"
echo "============================================"

###############################################################################
# Phase 1: Fix flintbox_base.py field mapping
###############################################################################

echo ""
echo "=== Phase 1a: Fix FlintboxScraper base class field mapping ==="
claude --print -p "
You are fixing the FlintboxScraper base class at src/scrapers/flintbox_base.py.

PROBLEM:
The _parse_api_item_with_detail() method fetches rich detail data (researchers, tags, ip_status, abstract, benefit, etc.) into raw_data, but NEVER populates the top-level Technology fields:
- innovators is always null (even though raw_data['researchers'] has data)
- keywords is always null (even though raw_data['flintbox_tags'] has data)
- patent_status is always null (even though raw_data['ip_status'] has data)
- description is often poor ('Invention Track Code...' instead of using abstract/other/benefit)

All 11 Flintbox scrapers (ucf, colorado, usc, usu, ttu, uconn, louisville, iowa + gatech, cmu, uiuc) inherit from this class, so fixing it fixes them all.

REFERENCE: Look at src/scrapers/warf.py _fetch_detail() method (lines 32-50) to see how WARF properly maps detail fields to Technology attributes.

TASK:
1. Read src/scrapers/flintbox_base.py
2. Read src/scrapers/warf.py for reference on field mapping
3. Modify flintbox_base.py _parse_api_item_with_detail() to also set:
   a. innovators: Extract researcher names from detail['_members'] (list of dicts with 'name' key)
   b. keywords: Use detail['_tags'] (list of strings)
   c. patent_status: Use detail.get('ipStatus') - map values like 'Filed', 'Issued', 'Pending', 'Provisional' etc.
   d. description: Prefer detail 'abstract' field (stripped of HTML), then 'other' field, then 'benefit', then key_points
4. Also check: does the base class description extraction strip HTML tags properly? The 'other' field may contain HTML.
5. Write a pytest test in tests/test_flintbox_base_detail.py that:
   - Mocks the Flintbox API detail endpoint to return known data with members, tags, ipStatus, abstract
   - Creates a FlintboxScraper subclass for testing
   - Verifies that after _parse_api_item_with_detail(), the Technology has correct innovators, keywords, patent_status, description
6. Run: python -m pytest tests/test_flintbox_base_detail.py -v
7. Fix any failures.
8. Run: python -m src.cli scrape --university ucf --limit 2
9. Verify the output shows populated innovators, keywords, patent_status, and good description.
10. Print the scraped Technology fields so user can verify.
11. If errors, append to SCRAPER_ERRORS.md.

IMPORTANT: Only modify flintbox_base.py and create test_flintbox_base_detail.py.
" --allowedTools "Bash,Read,Write,Edit,Glob,Grep"

###############################################################################
# Phase 1b: Fix standalone Flintbox scrapers (gatech, cmu, uiuc)
# These DON'T inherit from FlintboxScraper - they have their own copy of the code
###############################################################################

echo ""
echo "=== Phase 1b: Fix standalone Flintbox scrapers (gatech, cmu, uiuc) ==="
for uni in gatech cmu uiuc; do
  echo ""
  echo "--- Fixing $uni (standalone Flintbox, same field mapping issue) ---"
  claude --print -p "
You are fixing the $uni scraper at src/scrapers/$uni.py.

PROBLEM:
This scraper has its own _parse_api_item_with_detail() (copy/pasted from FlintboxScraper) that fetches detail data into raw_data but NEVER populates top-level Technology fields:
- innovators: always null even though raw_data['researchers'] has member data
- keywords: always null even though raw_data['flintbox_tags'] has tag data
- patent_status: always null even though raw_data['ip_status'] has status

TASK:
1. Read SCRAPER_ERRORS.md for known issues.
2. Read src/scrapers/$uni.py
3. Read src/scrapers/flintbox_base.py to see how it was just fixed (the _parse_api_item_with_detail now maps detail fields to Technology attributes).
4. Apply the SAME fix to $uni.py's _parse_api_item_with_detail():
   a. After building raw_data with detail fields, also set on the Technology:
      - innovators: [m['name'] for m in detail.get('_members', []) if m.get('name')]
      - keywords: detail.get('_tags') (list of strings)
      - patent_status: detail.get('ipStatus')
   b. Improve description selection: prefer abstract (HTML-stripped), then other (HTML-stripped), then benefit, then key_points
5. Write a pytest test in tests/test_${uni}_detail.py that verifies the fix works.
6. Run: python -m pytest tests/test_${uni}_detail.py -v
7. Fix failures.
8. Run: python -m src.cli scrape --university $uni --limit 2
9. Print the Technology fields for verification.
10. If errors, append to SCRAPER_ERRORS.md.

IMPORTANT: Only modify $uni.py and create test_${uni}_detail.py.
" --allowedTools "Bash,Read,Write,Edit,Glob,Grep"
done

###############################################################################
# Phase 1c: Fix cornell.py (standalone Flintbox, same issue)
###############################################################################

echo ""
echo "=== Phase 1c: Fix cornell (standalone Flintbox, same field mapping issue) ==="
claude --print -p "
You are fixing the Cornell scraper at src/scrapers/cornell.py.

PROBLEM: Same as other Flintbox scrapers - _parse_api_item_with_detail() populates raw_data but not top-level Technology fields (innovators, keywords, patent_status). Description is also poor.

TASK:
1. Read src/scrapers/cornell.py
2. Read src/scrapers/flintbox_base.py to see the fix pattern.
3. Apply the same fix: map detail fields to Technology innovators, keywords, patent_status, description.
4. Write test in tests/test_cornell_detail.py, run it, fix failures.
5. Run: python -m src.cli scrape --university cornell --limit 2
6. Print Technology fields for verification.
7. If errors, append to SCRAPER_ERRORS.md.

IMPORTANT: Only modify cornell.py and create test_cornell_detail.py.
" --allowedTools "Bash,Read,Write,Edit,Glob,Grep"

###############################################################################
# Phase 2: Fix TechPublisher scrapers that already have detail parsing
# These (uw, purdue, minnesota, princeton, michiganstate, texasstate) already
# have full WARF-style detail parsing. Check if they map fields properly.
###############################################################################

echo ""
echo "=== Phase 2: Verify/fix TechPublisher scrapers with existing detail parsing ==="
for uni in uw purdue minnesota princeton michiganstate texasstate; do
  echo ""
  echo "--- Checking $uni (TechPublisher with detail parsing) ---"
  claude --print -p "
You are verifying and fixing the $uni scraper at src/scrapers/$uni.py.

CONTEXT: This TechPublisher scraper already has detail page parsing (like WARF). But we need to verify it properly populates ALL Technology fields.

TASK:
1. Read SCRAPER_ERRORS.md
2. Read src/scrapers/$uni.py
3. Check if _fetch_detail() properly maps:
   - detail['full_description'] -> tech.description
   - detail['inventors'] -> tech.innovators
   - detail['categories'] -> tech.keywords
   - detail['patent_status'] -> tech.patent_status
   - detail['patent_table'] -> patent info in raw_data
   - detail['advantages'], detail['applications'], detail['publications'], detail['contact'] -> raw_data
4. If any mapping is missing, fix it.
5. Read src/scrapers/warf.py for reference if needed.
6. Write a pytest test in tests/test_${uni}_detail.py that:
   - Creates mock TechPublisher HTML
   - Verifies scrape_technology_detail() extracts fields correctly
   - Verifies _fetch_detail() properly maps to Technology attributes
7. Run: python -m pytest tests/test_${uni}_detail.py -v
8. Fix failures.
9. Run: python -m src.cli scrape --university $uni --limit 2
10. Print Technology fields for verification.
11. If errors, append to SCRAPER_ERRORS.md.

IMPORTANT: Only modify $uni.py if needed and create test_${uni}_detail.py.
" --allowedTools "Bash,Read,Write,Edit,Glob,Grep"
done

###############################################################################
# Phase 3: Fix Algolia scrapers with stub detail parsing
# buffalo, unlv, waynestate, northwestern, uf - need real TechPublisher HTML parsing
###############################################################################

echo ""
echo "=== Phase 3: Fix Algolia scrapers with stub scrape_technology_detail ==="
for uni in buffalo unlv waynestate northwestern uf; do
  echo ""
  echo "--- Fixing $uni (Algolia + stub detail) ---"
  claude --print -p "
You are enhancing the $uni scraper at src/scrapers/$uni.py.

CONTEXT:
- Uses Algolia API with rich descriptionFull parsing (sections, inventors, categories, IP status).
- scrape_technology_detail() is a stub returning {'url': url}.
- Detail pages at *.technologypublisher.com have same HTML structure as WARF.

TASK:
1. Read SCRAPER_ERRORS.md
2. Read src/scrapers/$uni.py carefully
3. Read src/scrapers/warf.py for TechPublisher HTML detail page parsing reference
4. Modify $uni.py:
   a. Add imports: asyncio, BeautifulSoup (from bs4)
   b. Add DETAIL_CONCURRENCY = 5 at module level
   c. Replace stub scrape_technology_detail() with real parsing (modeled on WARF):
      - full_description from .product-description-box / .description / .c_content
      - Structured sections (advantages, applications) from h2/h3/strong headings
      - Inventors from collapsible sections
      - Publications/references from collapsible sections
      - Documents from collapsible sections
      - Categories from breadcrumb/category links
      - Contact from mailto links
      - Patent table parsing
      - Patent numbers from Google Patents / USPTO links
   d. Add _fetch_detail() method that merges detail into Technology:
      - detail full_description -> tech.description (only if Algolia didn't provide one)
      - detail inventors -> tech.innovators (only if not already set)
      - detail categories -> tech.keywords (only if not already set)
      - detail patent_status -> tech.patent_status
      - All fields into tech.raw_data
   e. Modify scrape() to collect all techs first, then concurrent detail fetch with Semaphore(5)
5. Write pytest test in tests/test_${uni}_detail.py
6. Run tests, fix failures
7. Run: python -m src.cli scrape --university $uni --limit 2
8. Print Technology fields for verification
9. If errors, append to SCRAPER_ERRORS.md

IMPORTANT: Only modify $uni.py and create test_${uni}_detail.py.
" --allowedTools "Bash,Read,Write,Edit,Glob,Grep"
done

###############################################################################
# Phase 4: Fix JHU (Algolia with real but unwired detail parsing)
###############################################################################

echo ""
echo "=== Phase 4: Fix jhu (Algolia - detail parsing exists but not wired) ==="
claude --print -p "
You are enhancing the JHU scraper at src/scrapers/jhu.py.

CONTEXT:
- Uses Algolia API with category-based querying and rich descriptionFull parsing.
- Has real scrape_technology_detail() with _extract_patent_info_from_html() but NEVER calls it.

TASK:
1. Read SCRAPER_ERRORS.md
2. Read src/scrapers/jhu.py
3. Read src/scrapers/warf.py for concurrent detail fetch pattern
4. Modify jhu.py:
   a. Add DETAIL_CONCURRENCY = 5
   b. Add _fetch_detail() method that merges patent info from detail into Technology
   c. Modify scrape() to collect all techs, then concurrent detail fetch with Semaphore(5)
   d. Map detail fields: patent_numbers, serial_numbers, ip_status -> raw_data and tech.patent_status
5. Write test in tests/test_jhu_detail.py
6. Run tests, fix failures
7. Run: python -m src.cli scrape --university jhu --limit 2
8. Print Technology fields
9. If errors, append to SCRAPER_ERRORS.md

IMPORTANT: Only modify jhu.py and create test_jhu_detail.py.
" --allowedTools "Bash,Read,Write,Edit,Glob,Grep"

###############################################################################
# Phase 5: Fix custom scrapers with unwired detail parsing
###############################################################################

echo ""
echo "=== Phase 5a: Fix columbia (detail parsing exists but not wired) ==="
claude --print -p "
You are enhancing the Columbia scraper at src/scrapers/columbia.py.

CONTEXT:
- Gets URLs from sitemap but only parses title/ID from URL slug - NO content fetched.
- Has scrape_technology_detail() that extracts description, patent info from HTML.
- scrape() never calls scrape_technology_detail().

TASK:
1. Read SCRAPER_ERRORS.md
2. Read src/scrapers/columbia.py
3. Read src/scrapers/warf.py for concurrent detail fetch pattern
4. Modify columbia.py:
   a. Add DETAIL_CONCURRENCY = 5
   b. Add _fetch_detail() that calls scrape_technology_detail() and merges results
   c. Enhance scrape_technology_detail() to also extract: title from <h1>/<title>, full description from main content, inventors/researchers, categories, advantages, applications, contact info
   d. Modify scrape() to collect all URL-based techs, then concurrent detail fetch
   e. Map: description, innovators, keywords, patent_status onto Technology
5. Write test in tests/test_columbia_detail.py
6. Run tests, fix failures
7. Run: python -m src.cli scrape --university columbia --limit 2
8. Print Technology fields
9. If errors, append to SCRAPER_ERRORS.md

IMPORTANT: Only modify columbia.py and create test_columbia_detail.py.
" --allowedTools "Bash,Read,Write,Edit,Glob,Grep"

echo ""
echo "=== Phase 5b: Fix mit (detail parsing exists but not wired) ==="
claude --print -p "
You are enhancing the MIT scraper at src/scrapers/mit.py.

CONTEXT:
- Scrapes technology teasers with basic info (title, case number, categories, researchers, description).
- Has scrape_technology_detail() extracting full_description, problem, solution, advantages, patent info.
- scrape() never calls scrape_technology_detail().

TASK:
1. Read SCRAPER_ERRORS.md
2. Read src/scrapers/mit.py
3. Read src/scrapers/warf.py for concurrent detail fetch pattern
4. Modify mit.py:
   a. Add DETAIL_CONCURRENCY = 5
   b. Add _fetch_detail() method
   c. Modify scrape() to collect all techs from all pages, then concurrent detail fetch with Semaphore(5)
   d. Map detail fields to Technology: full_description -> description (if richer), problem/solution/advantages -> raw_data, patent info -> patent_status and raw_data
5. Write test in tests/test_mit_detail.py
6. Run tests, fix failures
7. Run: python -m src.cli scrape --university mit --limit 2
8. Print Technology fields
9. If errors, append to SCRAPER_ERRORS.md

IMPORTANT: Only modify mit.py and create test_mit_detail.py.
" --allowedTools "Bash,Read,Write,Edit,Glob,Grep"

###############################################################################
# Phase 6: Verify/fix remaining custom scrapers that are supposedly enriched
###############################################################################

echo ""
echo "=== Phase 6: Verify/fix remaining custom scrapers ==="
for uni in harvard duke upenn ucsystem utaustin umich; do
  echo ""
  echo "--- Checking $uni (Custom with detail parsing) ---"
  claude --print -p "
You are verifying and fixing the $uni scraper at src/scrapers/$uni.py.

CONTEXT: This scraper supposedly has detail page parsing wired up. Verify it populates ALL Technology fields correctly.

TASK:
1. Read SCRAPER_ERRORS.md
2. Read src/scrapers/$uni.py
3. Check that _fetch_detail() or equivalent properly maps:
   - full_description -> tech.description
   - inventors/researchers -> tech.innovators
   - categories/tags -> tech.keywords
   - patent/IP status -> tech.patent_status
   - advantages, applications, publications, contact -> tech.raw_data
4. If any mapping is missing or broken, fix it.
5. Write pytest test in tests/test_${uni}_detail.py
6. Run tests, fix failures
7. Run: python -m src.cli scrape --university $uni --limit 2
8. Print Technology fields to verify all are populated
9. If errors, append to SCRAPER_ERRORS.md

IMPORTANT: Only modify $uni.py if needed and create test_${uni}_detail.py.
" --allowedTools "Bash,Read,Write,Edit,Glob,Grep"
done

###############################################################################
# Phase 7: Verify Stanford (reference scraper, should be fine)
###############################################################################

echo ""
echo "=== Phase 7: Verify stanford ==="
claude --print -p "
Quick verification of the Stanford scraper at src/scrapers/stanford.py.

TASK:
1. Read src/scrapers/stanford.py
2. Run: python -m src.cli scrape --university stanford --limit 2
3. Print Technology fields (title, description[:100], innovators, keywords, patent_status, raw_data keys)
4. If any top-level fields are null that shouldn't be, fix the scraper.
5. If errors, append to SCRAPER_ERRORS.md.
" --allowedTools "Bash,Read,Write,Edit,Glob,Grep"

echo ""
echo "============================================"
echo "All 33 scrapers processed!"
echo "============================================"
echo "Check SCRAPER_ERRORS.md for any issues encountered."
echo "Verify results at http://localhost:5173"

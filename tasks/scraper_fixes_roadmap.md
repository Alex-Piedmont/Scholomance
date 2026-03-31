# Scraper Fixes Roadmap — Tier 2 & Tier 3

## Status
Tier 1 scrapers (CMU, Stanford, UT Austin, UPenn) are being fixed and QA'd.
UConn base class changes (flintbox_base.py) are already deployed but UConn itself needs re-QA.

---

## Tier 2: Medium Fixes

### UConn (Flintbox Base) — CHANGES ALREADY DEPLOYED, NEEDS QA
- **flintbox_base.py changes applied**: embedded section parsing on `benefit` field, bullet fix (`·•` → `- `), `publications` in cleaning loop, `key_points` HTML entity cleanup
- **Next step**: Scrape 5 docs and visually QA at localhost:5173
- **Known risk**: Bullet change affects all Flintbox scrapers — USU sanity check passed but visual QA recommended
- **Follow-up action from SCRAPER_PLAN.md**: Fix `&nbsp;` in Market Opportunity; missing bullets in Market Application; full re-scrape needed

### Princeton (RSS Feed)
File: `src/scrapers/princeton.py`
Issues found by analysis:
1. **Section bleed (CRITICAL)**: `heading.parent.find_next_sibling()` fallback causes all subsequent page content (inventor bios, contacts, IP status) to bleed into `applications` and `advantages` arrays. **Fix**: Remove the parent-fallback. Only walk direct siblings, stop at next heading.
2. **`full_description` → `background`**: Description content maps to `full_description` but frontend expects `background`. Change the heading parser to store description sections as `background`.
3. **`problem` → `technical_problem`**: Wrong key name.
4. **`development_stage` misses "Intellectual Property Status"**: Add `"intellectual property" in htxt` to condition.
5. **`full_description` from `.c_content` is noisy**: Captures entire page including metadata, headings, contacts. Remove or restrict selector.
6. **~60% of detail pages return errors**: Site-level issue ("Page parameter in incorrect format"), not a scraper bug.

### Texas State (RSS Feed)
File: `src/scrapers/texasstate.py`
Issues found by analysis:
1. **`background` not populated**: "description" heading content goes to `full_description` instead. Change to `background`.
2. **Patent table grabs layout table**: `soup.find("table")` finds a page wrapper table. Fix: iterate `find_all("table")` and check for patent-related headers.
3. **`ip_status` not populated**: Need to construct from parsed patent table rows (type | country | serial | date | status).
4. **`patent_status` incorrectly "Granted"**: Root cause is the layout table match. Fixing the table selector resolves this.
5. **`full_description` contains entire page dump**: Remove `.c_content` fallback.
6. **`problems_solved` → `technical_problem`**: Wrong key name.

### Buffalo (Algolia API)
File: `src/scrapers/buffalo.py`
Issues found by analysis:
1. **RSS XML tag parser rewrite (CRITICAL)**: `_parse_description_sections()` uses plain-text header regex but data uses `<RSS.XXX>` XML tags. Need to rewrite to extract from `<RSS.Tag>content</RSS.Tag>` pairs.
2. **Tag mapping**: `RSS.AlgoliaSummary` → `short_description`, `RSS.Background` → `background`, `RSS.Technology` → `solution`, `RSS.Advantages` → `advantages` (array, tab-delimited), `RSS.Application` → `applications` (array, tab-delimited), `RSS.PatentStatus` → `ip_status`, `RSS.StageOfDevelopment` → `development_stage`
3. **Update raw_data keys**: Add `solution`, `technical_problem` to the output key list.

### UF (Algolia API)
File: `src/scrapers/uf.py`
Issues found by analysis:
1. **"Application" (singular) not matched**: UF data uses title-case singular "Application" (97/100 techs). Add pattern mapped to `market_application`.
2. **No "Technology" pattern**: Add `TECHNOLOGY` mapped to `solution` in section_patterns.
3. **`short_description` from preamble**: Extract first line before first section header.
4. **`advantages` stored as string**: Split tab-delimited items into array.
5. **Missing raw_data keys**: Add `market_application`, `solution`, `technical_problem`.

---

## Tier 3: Significant Work

### UC System (Custom)
File: `src/scrapers/ucsystem.py`
Issues found by analysis:
1. **No section parsing at all (CRITICAL)**: Pages use `<h3>` headings (Abstract, Full Description, Applications, Features/Benefits, Patent Status, Inventors, Contact) but scraper doesn't parse any of them. Need full h3-walking loop.
2. **Mapping**: Abstract → `background`, Full Description → `full_description`, Applications → `applications` (array), Features/Benefits → `advantages` (array), Patent Status → `ip_status`, Inventors → `inventors` (array)
3. **Campus detection broken**: `?campus=` link captures "Available Technologies". Use text search instead.
4. **500-char description truncation**: Remove truncation, use `full_description`/`background`.
5. **`•` bullet markers**: Need to split into arrays when sections are plain text.

### MIT (Custom)
File: `src/scrapers/mit.py`
Issues found by analysis:
1. **Detail pages never scraped (CRITICAL)**: `scrape_technology_detail()` exists but is never called from `scrape()`. Need to wire it up with 1-second rate limiting.
2. **Detail parser uses wrong CSS classes**: Rewrite to use: `div.tech-brief-details__intro` → `background`, `div.tech-brief-body__inner` h2 headings → `solution`/`technical_problem`/`advantages`, `div.tech-brief-details__ip` → `ip_status`
3. **`technology_areas` always empty**: Parse plain text split on `/` instead of `<a>` tags.
4. **`case_number` always None**: Fix selector from `div` to `span`, fix regex.
5. **`researchers` format mismatch**: Split on ` / ` not `,`; format as `[{name: "..."}]`.
6. **Titles missing spaces**: Replace `<br>` with space before `get_text()`.
7. **~2800+ technologies**: Detail scraping at 1s/request = ~47 minutes for full scrape.

---

## Cross-Cutting Patterns to Watch
1. **Sibling-walking bleed**: Princeton, UPenn, Texas State all have the `heading.parent.find_next_sibling()` antipattern
2. **Wrong field keys**: `problem` → `technical_problem`, `ip_info` → `ip_status`, `opportunity` → `market_opportunity`
3. **`get_text(strip=True)` word concatenation**: Use `separator=" "` when inline tags exist

---

## Follow-up Actions (from SCRAPER_PLAN.md)
| University | Action |
|-----------|--------|
| `ttu` | Full re-scrape needed (embedded section parsing applied to ~100/323 techs) |
| `cornell` | Full re-scrape needed (section parsing applied to ~298/1114 techs) |
| `michiganstate` | Full re-scrape needed (detail parser applied to ~15/340 techs) |
| `columbia` | Full re-scrape needed (detail fetching applied to ~15/1211 techs) |
| `gatech` | API returns 500 error on page 18; only 408/~744 techs scraped; retry later |

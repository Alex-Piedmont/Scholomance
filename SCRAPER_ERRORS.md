# Scraper Error / Solution Log

**IMPORTANT INSTRUCTION: When you encounter an error while working on a scraper, CHECK THIS FILE FIRST. The same or similar issue may have already been solved for another scraper. Do not waste time re-investigating problems that have known solutions.**

---

| University | Problem | Solution |
|-----------|---------|----------|
| `usu` | Metadata strings (IP status, dev stage) leaking into `other` field | Added `_is_metadata()` filter in `flintbox_base.py` |
| `ttu` | Raw HTML (`<br>`, `·&nbsp;`) in `market_application`/`benefit`; embedded sections (IP, dev stage, keywords) not parsed | Extended `_parse_embedded_sections()` for all section types; added BeautifulSoup HTML cleaning in `flintbox_base.py` |
| `cornell` | Abstract and Technology Overview merged; Publications/Patents absent; no HTML cleaning | Separated background/overview in `_parse_embedded_sections()`; added publications fallback from `publications_html`; duplicated HTML cleaning loop in `cornell.py` |
| `warf` | All content in `full_description` with markdown bold headers; authors not parsed from nested divs; Included IP not separated | Rewrote detail parser: invention/overview→`abstract`, applications/advantages→arrays, Included IP→`ip_text`; fixed author parsing for `div > div` structure |
| `michiganstate` | `&nbsp;` in description; detail page content not structured into sections | Rewrote detail parser with `<p>` heading detection for known section names; added `subtitle` for Executive Summary; added keyword parsing from "Key Words" section |
| `columbia` | `description=None` despite having page content; no detail page fetching | Added `_fetch_detail()` with concurrency; built section parser mapping h2 headings to standard raw_data field names |
| `purdue` | Sections not parsed; inventors concatenated | Added section parsing + inventor splitting |
| `uw` | Section headings use `<h6>` tags instead of h2/h3/strong; all content in `full_description` | Added h6 to heading search; mapped Problem→`background`, Solution→`abstract`, Patent→`ip_status`; fixed inventor parsing for nested div structure |
| `minnesota` | `<h2>` section content (TRL, Researchers) missed because inline `<b>`/text nodes after h2 not captured; researcher names split on commas breaking "Name, PhD"; stale `researchers` array (strings) blocking `inventors` display | Added inline content collection after h2/h3; parse researcher names from `<b>` tags in `<li>` items with degree stripping; store as `inventors` not `researchers` to avoid frontend conflict (SidePanel shows researchers over inventors) |

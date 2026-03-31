# Scholomance Refactor Roadmap

## Completed - Cleanup Phase (2026-03-12)

- [x] Deleted stale root files (PLAN.md, PROMPT.md, RALPH_GUIDE.md, build_dashboard.sh, fix_scrapers.sh, etc.)
- [x] Removed 108MB ralphblaster.log and empty SQLite files
- [x] Cleaned up htmlcov/, university_tech_scraper.egg-info/, .docx temp files
- [x] Deleted all 8 one-off scripts in scripts/ (duke investigation, flintbox credential extraction, init_db.sql)
- [x] Removed unused Alembic migration infrastructure (alembic.ini, migrations/)
- [x] Deleted test_coverage_boost.py, merged 7 useful tests into proper test files
- [x] Refactored test_phase4.py → test_scheduler.py, removed dead Alembic/Docker config tests
- [x] Fixed pyproject.toml missing deps (fastapi, uvicorn, aiohttp)
- [x] Fixed Dockerfile.railway to use requirements-api.txt
- [x] Updated .gitignore (added *.dump, *.docx; removed .dashboard_progress)
- [x] Deleted redundant setup.py

## Completed - Flintbox Scraper Refactor (2026-03-17)

- [x] Converted cornell.py, gatech.py, uga.py, uiuc.py from standalone ~420-line scrapers to 13-line thin FlintboxScraper subclasses (eliminated ~1,600 lines of duplicated code)
- [x] Extracted parsing utilities into new flintbox_parsing.py (parse_embedded_sections, clean_html_text, is_metadata, clean_html_field)
- [x] Decomposed monolithic _parse_api_item_with_detail (250 lines) into focused methods: _merge_detail_fields, _apply_benefit_fallback, _extract_publication_links, _clean_raw_data_fields, _build_description, _extract_top_level_fields
- [x] Added ENABLE_BENEFIT_FALLBACK class attribute to gate benefit-as-abstract fallback
- [x] Removed _init_browser/_close_browser backwards-compat stubs
- [x] All 13 Flintbox scrapers now share the same inheritance path; all 35 scrapers load successfully

## Next Steps

### Scheduler / Cron Job Infrastructure
- [ ] APScheduler dependency is declared but was not installed in dev environment — indicates the scheduler module has never been exercised in production
- [ ] Decide: is the scheduler the right approach for production recurring scrapes, or should this move to an external cron/task system (Railway cron jobs, GitHub Actions scheduled workflows, etc.)?
- [ ] If keeping APScheduler: ensure it's installed in all environments, add CI test coverage
- [ ] If migrating to external cron: refactor scheduler.py to be a simple CLI entrypoint that cron calls, remove APScheduler dependency
- [ ] The `migrate` CLI command references Alembic which we removed — either remove the command or implement a simpler migration approach
- [ ] Parallelize multi-university scrapes with `asyncio.gather()` + configurable `Semaphore` concurrency limit (scrapers hit different domains so no rate-limit conflict; cap concurrent Playwright instances to control memory)

### Test Suite Health
- [ ] Consider renaming test_phase3_scrapers.py → test_gatech_uga_scrapers.py for clarity
- [ ] Add CI pipeline to catch import errors and silently-skipped test modules
- [ ] Ensure all declared dependencies are installed in test environments

### Dependency Management
- [ ] Decide on single source of truth: pyproject.toml vs requirements.txt
- [ ] Consider removing requirements.txt and having Dockerfiles install from pyproject.toml directly
- [ ] Keep requirements-api.txt as curated Railway-specific subset (documented)

### Scraper Fixes (Tier 2 & 3)
- [ ] See detailed roadmap: `tasks/scraper_fixes_roadmap.md`
- [ ] Tier 2: UConn QA, Princeton, Texas State, Buffalo, UF
- [ ] Tier 3: UC System (no section parsing), MIT (detail pages never scraped)
- [ ] Follow-up re-scrapes: ttu, cornell, michiganstate, columbia, gatech

### Schema Management
- [ ] schema.sql is kept as human-readable reference; SQLAlchemy ORM is the runtime source of truth
- [ ] field_taxonomy table exists in schema.sql but has no SQLAlchemy model — decide if it's needed
- [ ] Document the initialization flow (Base.metadata.create_all vs psql -f schema.sql)

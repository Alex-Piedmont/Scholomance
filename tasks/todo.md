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

## Next Steps

### Scheduler / Cron Job Infrastructure
- [ ] APScheduler dependency is declared but was not installed in dev environment — indicates the scheduler module has never been exercised in production
- [ ] Decide: is the scheduler the right approach for production recurring scrapes, or should this move to an external cron/task system (Railway cron jobs, GitHub Actions scheduled workflows, etc.)?
- [ ] If keeping APScheduler: ensure it's installed in all environments, add CI test coverage
- [ ] If migrating to external cron: refactor scheduler.py to be a simple CLI entrypoint that cron calls, remove APScheduler dependency
- [ ] The `migrate` CLI command references Alembic which we removed — either remove the command or implement a simpler migration approach

### Test Suite Health
- [ ] Consider renaming test_phase3_scrapers.py → test_gatech_uga_scrapers.py for clarity
- [ ] Add CI pipeline to catch import errors and silently-skipped test modules
- [ ] Ensure all declared dependencies are installed in test environments

### Dependency Management
- [ ] Decide on single source of truth: pyproject.toml vs requirements.txt
- [ ] Consider removing requirements.txt and having Dockerfiles install from pyproject.toml directly
- [ ] Keep requirements-api.txt as curated Railway-specific subset (documented)

### Schema Management
- [ ] schema.sql is kept as human-readable reference; SQLAlchemy ORM is the runtime source of truth
- [ ] field_taxonomy table exists in schema.sql but has no SQLAlchemy model — decide if it's needed
- [ ] Document the initialization flow (Base.metadata.create_all vs psql -f schema.sql)

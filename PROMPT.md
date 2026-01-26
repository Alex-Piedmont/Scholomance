# University Tech Transfer Database Scraper

## Project Goal
Build a searchable database system that scrapes invention listings from university tech transfer websites. Start with Stanford as MVP, then expand to Georgia Tech and UGA.

## Success Criteria
Output `<promise>PHASE_COMPLETE</promise>` when current phase is fully working with passing tests.

---

## PHASE 1: Stanford MVP (START HERE)

### Requirements
1. **PostgreSQL Database Setup**
   - Create schema with tables for technologies
   - Include fields: university, tech_id, title, description, url, scraped_at, raw_data (JSONB)
   - Add derived fields: top_field, subfield, patent_geography
   - Ensure UNIQUE constraint on (university, tech_id)

2. **Stanford Scraper**
   - Use Playwright (Python) to handle JavaScript rendering
   - Scrape https://techfinder.stanford.edu
   - Handle pagination (130 pages, ~1942 technologies)
   - Extract: tech_id, title, description, innovators, keywords, URL
   - Store all extracted data in database

3. **CLI Interface**
   - Command: `scrape --university stanford` (ad hoc scrape)
   - Command: `scrape --all` (runs all configured universities)
   - Command: `schedule --weekly` (sets up scheduled task)
   - Use click or typer for CLI framework

4. **Basic Search/Filter**
   - Simple command to query database
   - Filter by: university, keyword search in title/description
   - Output results to stdout or JSON

### Verification Steps
- [ ] Database schema created and can be initialized
- [ ] Scraper successfully fetches at least 50 Stanford technologies
- [ ] Data is properly stored in PostgreSQL with no duplicates
- [ ] CLI commands execute without errors
- [ ] Basic search returns relevant results
- [ ] All dependencies listed in requirements.txt
- [ ] README documents how to run the scraper

### Testing Requirements
- Unit tests for database operations (insert, query, update)
- Integration test: scrape 1 page from Stanford and verify data storage
- CLI test: ensure commands parse correctly
- Aim for >70% test coverage

### Technical Constraints
- Python 3.11+
- Use asyncio for async operations
- Playwright for web scraping (handles JS rendering)
- PostgreSQL for data storage
- Environment variables for database credentials
- Clean error handling and logging

### If Stuck After 15 Iterations
Document:
1. What's blocking progress (specific error or architectural decision)
2. What approaches were attempted
3. Suggested alternative approaches or simplifications
4. Consider: Can we simplify (e.g., fewer fields, simpler scraping)?

### Completion Promise
When Phase 1 is complete with:
- ✅ Working Stanford scraper
- ✅ Data stored in PostgreSQL
- ✅ CLI commands functional
- ✅ Basic tests passing
- ✅ README with setup instructions

Output: `<promise>PHASE_COMPLETE</promise>`

---

## PHASE 2: LLM Classification (After Phase 1)

### Requirements
1. **Add Classification Service**
   - Integrate Claude API for text classification
   - Send technology descriptions to classify top_field and subfield
   - Store classifications in database
   - Handle rate limiting appropriately

2. **Classification Schema**
   - Top-level fields: Robotics, MedTech, Agriculture, Energy, Computing, Materials, etc.
   - Subfields: domain-specific (e.g., "small molecule drugs", "agtech sensors")
   - Use structured prompt for consistent classification

3. **CLI Enhancement**
   - Command: `classify --batch 100` (classify unclassified techs)
   - Command: `classify --university stanford --force` (re-classify all)

### Verification Steps
- [ ] Claude API integration works
- [ ] Classifications are stored correctly
- [ ] Can filter/search by top_field and subfield
- [ ] Handles API errors gracefully
- [ ] Cost tracking or limits in place

Output: `<promise>PHASE_COMPLETE</promise>` when classification is working

---

## PHASE 3: Multi-University Support (After Phase 2)

### Requirements
1. **Georgia Tech Scraper**
   - Scrape https://licensing.research.gatech.edu/technology-licensing
   - Requires JavaScript - use same Playwright approach
   - Map their fields to our standardized schema

2. **UGA Scraper (Flintbox)**
   - Scrape https://uga.flintbox.com/technologies
   - JavaScript-heavy React app
   - May need to inspect network requests for data

3. **Scraper Registry**
   - Configuration file listing all universities and their scraper modules
   - Easy to add new universities

### Verification Steps
- [ ] Georgia Tech scraper works and stores data
- [ ] UGA scraper works and stores data
- [ ] `scrape --all` runs all three universities
- [ ] No conflicts between university data
- [ ] Tests cover all three scrapers

Output: `<promise>PHASE_COMPLETE</promise>` when all three universities work

---

## PHASE 4: Scheduling & Production Ready (After Phase 3)

### Requirements
1. **Scheduled Scraping**
   - Weekly cron job or scheduled task
   - Incremental scraping (detect new/updated technologies)
   - Email notifications on failures

2. **Enhanced Filtering**
   - Filter by patent geography
   - Filter by top_field and subfield
   - Date range filtering
   - Export results (CSV, JSON)

3. **Production Hardening**
   - Comprehensive error handling
   - Retry logic for failed scrapes
   - Logging to files
   - Database migration system
   - Docker deployment option

Output: `<promise>PROJECT_COMPLETE</promise>` when production-ready

---

## General Guidelines
- **Write tests first** when possible (TDD approach)
- **Run tests after each implementation** - if tests fail, debug before continuing
- **Commit frequently** with clear messages
- **Document as you go** - update README with setup steps
- **Use environment variables** for secrets (never hardcode credentials)
- **Log everything** - use Python logging module
- **Handle errors gracefully** - expect network failures, missing data, etc.

## Project Structure Suggestion
```
university-tech-scraper/
├── README.md
├── requirements.txt
├── .env.example
├── setup.py or pyproject.toml
├── src/
│   ├── __init__.py
│   ├── cli.py              # CLI entry point
│   ├── database.py         # Database models and operations
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py         # Base scraper class
│   │   ├── stanford.py
│   │   ├── gatech.py
│   │   └── uga.py
│   ├── classifier.py       # LLM classification service
│   └── scheduler.py        # Scheduling logic
├── tests/
│   ├── test_database.py
│   ├── test_scrapers.py
│   └── test_cli.py
└── scripts/
    └── init_db.sql         # Database schema
```

## Important Notes
- Start simple, iterate to add features
- Each phase builds on the previous
- Don't aim for perfect on first try - let the loop refine
- If you hit a blocker, document it and move to next solvable piece
- Prioritize working code over perfect code

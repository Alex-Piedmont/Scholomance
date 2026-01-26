# University Tech Transfer Database Scraper

A system for scraping and searching university technology transfer listings. Built to aggregate invention disclosures from 50-100+ universities into a standardized, searchable database.

## Project Status
🚧 **In Development** - Built via Claude Code Ralph Wiggum loop

## Overview
This tool scrapes technology licensing opportunities from university tech transfer offices, standardizes the data, and provides searchable access with classification by field and subfield.

### Target Universities (Initial)
1. **Stanford** - https://techfinder.stanford.edu (~1942 technologies)
2. **Georgia Tech** - https://licensing.research.gatech.edu/technology-licensing
3. **UGA** - https://uga.flintbox.com/technologies

### Key Features
- Multi-university scraping with format adaptation
- PostgreSQL storage with JSONB for flexibility
- LLM-based classification (top_field, subfield)
- CLI interface for ad-hoc and scheduled scraping
- Filterable by patent geography, field, subfield, keywords

## Tech Stack
- **Python 3.11+**
- **PostgreSQL** - Database
- **Playwright** - Web scraping (handles JavaScript)
- **Click/Typer** - CLI framework
- **Claude API** - Technology classification
- **asyncio** - Async operations

## Quick Start

### Prerequisites
```bash
# Install PostgreSQL
# macOS: brew install postgresql
# Ubuntu: sudo apt-get install postgresql

# Install Python 3.11+
python --version  # Verify 3.11+
```

### Installation
```bash
# Clone repository
git clone <repo-url>
cd Scholomance

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Install Playwright browsers
playwright install chromium

# Set up database
cp .env.example .env
# Edit .env with your database credentials

# Initialize database schema (requires PostgreSQL running)
psql -d your_database -f schema.sql

# Or use the CLI to create basic tables:
python -m src.cli init-db
```

### Usage
```bash
# Scrape a single university
python -m src.cli scrape --university stanford

# Scrape all configured universities
python -m src.cli scrape --all

# Classify technologies using LLM
python -m src.cli classify --batch 100

# Search the database
python -m src.cli search --keyword "robotics" --field "Engineering"

# Set up weekly scheduled scraping
python -m src.cli schedule --weekly
```

## Development

### Running Tests
```bash
pytest tests/ -v --cov=src
```

### Project Structure
```
university-tech-scraper/
├── src/
│   ├── cli.py              # CLI interface
│   ├── database.py         # Database models
│   ├── scrapers/           # University-specific scrapers
│   ├── classifier.py       # LLM classification
│   └── scheduler.py        # Scheduling logic
├── tests/                  # Test suite
├── scripts/                # Utility scripts
└── PROMPT.md              # Ralph loop instructions
```

## Architecture Notes

### Data Flow
1. **Scraper** → Playwright loads university site → Extract data
2. **Parser** → Normalize to standard schema → Store raw_data as JSONB
3. **Classifier** → LLM reads description → Assign top_field/subfield
4. **Database** → PostgreSQL stores standardized + raw data
5. **CLI** → Query interface with filtering

### Schema Design
- **Core fields**: university, tech_id, title, description, url
- **JSONB raw_data**: Preserves all original fields
- **Derived fields**: top_field, subfield, patent_geography (added post-scrape)
- **Unique constraint**: (university, tech_id)

### Extensibility
Adding a new university:
1. Create scraper class in `src/scrapers/new_university.py`
2. Inherit from `BaseScraper`
3. Implement `scrape()` method
4. Add to university registry

## Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/techdb

# Claude API (for classification)
ANTHROPIC_API_KEY=sk-ant-...

# Scraping
USER_AGENT=UniversityTechScraper/1.0
SCRAPE_DELAY=1.0  # Seconds between requests
```

### Scheduling Options
- **Cron** (Linux/Mac): `0 2 * * 0` (2 AM every Sunday)
- **Task Scheduler** (Windows): Weekly trigger
- **Cloud**: AWS EventBridge, Google Cloud Scheduler

## Roadmap

### Phase 1: Stanford MVP ✅
- [x] PostgreSQL schema
- [x] Stanford scraper with Playwright
- [x] CLI interface
- [x] Basic search/filter

### Phase 2: Classification
- [ ] Claude API integration
- [ ] Batch classification
- [ ] Field/subfield taxonomy

### Phase 3: Multi-University
- [ ] Georgia Tech scraper
- [ ] UGA Flintbox scraper
- [ ] Scraper registry system

### Phase 4: Production
- [ ] Weekly scheduled scraping
- [ ] Incremental updates
- [ ] Enhanced filtering
- [ ] Docker deployment

## Best Practices (Ralph Loop Guidance)
- ✅ Write tests first (TDD)
- ✅ Run tests after each change
- ✅ Commit frequently
- ✅ Log everything
- ✅ Handle errors gracefully
- ✅ Use environment variables for secrets

## Contributing
This project is built iteratively using the Ralph Wiggum technique. See `PROMPT.md` for the full build specification.

## License
MIT

## Contact
[Your contact info]

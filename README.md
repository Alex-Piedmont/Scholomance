# University Tech Transfer Database 

A system for consolidating and searching university technology transfer listings. Built to aggregate invention disclosures from dozens of universities into a standardized, searchable database to expedite analysis of commercial viability.

## Project Status
🚧 **In Development** - Deployed to a private website (available upon request). Currently includes data on 22k technologies across 34 universities. Current roadmap focuses on a means to identify the most valuable opportunities.  

## Overview
This tool collects technology licensing opportunities from university tech transfer offices, standardizes the data, and provides searchable access with classification by field and subfield.

### Exemplary Universities
1. **Stanford** 
2. **Georgia Tech** 
3. **University of California System** 

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


## Development


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
└── PROMPT.md              # CLI instructions
```

## Architecture Notes


### Schema Design
- **Core fields**: university, tech_id, title, description, url
- **JSONB raw_data**: Preserves all original fields
- **Derived fields**: top_field, subfield, patent_geography (added post-scrape)
- **Unique constraint**: (university, tech_id)


## Deployment

- **Frontend (Vercel)**: The Vercel project must have **Root Directory** set to `web` in Project Settings → General. Without this, Vercel detects Python at the repo root (via `requirements.txt` / `pyproject.toml`) and fails to install the frontend's npm dependencies, causing `vite: command not found` during build.
- **Backend (Railway)**: Builds from `Dockerfile.railway` at the repo root; see `railway.toml`.

## Contributing
This project was developed by Alex Rudd, Ph.D., with assistance from Anthropic's Claude Code. 

## License
MIT

## Contact
[Your contact info]

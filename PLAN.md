# Web Dashboard Implementation Plan

## Overview
Build a local web dashboard for viewing university technology transfer data with interactive analytics, filtering, and drill-down capabilities.

## Ralph Wiggum Loop

A bash script tracks progress through discrete steps. Each step is self-contained and can be executed in a fresh Claude context window. Run the loop, complete a step, then re-run to get the next task.

**Usage:**
```bash
./build_dashboard.sh        # Shows current step and instructions
./build_dashboard.sh done   # Marks current step complete, advances to next
./build_dashboard.sh status # Shows all steps and progress
```

**Steps:**
1. `api-setup` - Create FastAPI app skeleton with CORS and health check
2. `api-stats` - Add /api/stats/* endpoints for analytics data
3. `api-technologies` - Add /api/technologies endpoints with filtering/pagination
4. `api-cli` - Add `serve` command to CLI
5. `web-scaffold` - Create React + Vite + Tailwind project structure
6. `web-api-client` - Create API client and React hooks
7. `web-layout` - Build layout components (sidebar, header, routing)
8. `web-dashboard` - Build dashboard page with charts
9. `web-browser` - Build technology browser with filters and table
10. `web-detail` - Build detail page with iframe toggle
11. `web-integration` - Wire up cross-filtering and final polish
12. `production` - Configure production build and static serving

Each step includes:
- Clear deliverables
- Files to create/modify
- Test criteria to verify completion

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│  ┌─────────────────┬─────────────────┬─────────────────────────┐│
│  │   Dashboard     │   Technology    │      Detail View        ││
│  │   (Analytics)   │   Browser       │   (Data + Iframe)       ││
│  └─────────────────┴─────────────────┴─────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                              │
│  /api/stats, /api/technologies, /api/technologies/{id}          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL (existing)                         │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

**Backend:**
- FastAPI (Python) - REST API endpoints
- SQLAlchemy (existing) - Database ORM
- Uvicorn - ASGI server

**Frontend:**
- React 18 with TypeScript
- Vite - Build tool
- Recharts - Charts/visualizations
- TanStack Table - Data tables with sorting/filtering
- React Router - Navigation
- Tailwind CSS - Styling

## Implementation Tasks

### Phase 1: Backend API (FastAPI)

1. **Create API module** (`src/api/`)
   - `main.py` - FastAPI app with CORS for local dev
   - `routes/stats.py` - Analytics endpoints
   - `routes/technologies.py` - Technology CRUD/search
   - `schemas.py` - Pydantic response models

2. **API Endpoints:**
   ```
   GET /api/stats/overview
     → total_technologies, by_field, by_university, by_year

   GET /api/stats/fields
     → breakdown by top_field and subfield with counts

   GET /api/stats/universities
     → list of universities with tech counts, last scraped

   GET /api/stats/timeline
     → technologies by month/year (first_seen distribution)

   GET /api/technologies
     → paginated list with filters (field, university, date range, search)
     → query params: page, limit, q, top_field, subfield, university, from_date, to_date

   GET /api/technologies/{uuid}
     → single technology with full details

   GET /api/taxonomy
     → field/subfield hierarchy for filter dropdowns
   ```

3. **Add to CLI:**
   - `tech-scraper serve` command to run the web server
   - Options: --host, --port, --reload

### Phase 2: React Frontend

1. **Project Setup** (`web/`)
   ```
   web/
   ├── src/
   │   ├── components/
   │   │   ├── Dashboard/
   │   │   │   ├── OverviewCards.tsx
   │   │   │   ├── FieldChart.tsx
   │   │   │   ├── UniversityChart.tsx
   │   │   │   ├── TimelineChart.tsx
   │   │   │   └── GeographyChart.tsx
   │   │   ├── TechnologyBrowser/
   │   │   │   ├── FilterPanel.tsx
   │   │   │   ├── TechnologyTable.tsx
   │   │   │   └── Pagination.tsx
   │   │   ├── TechnologyDetail/
   │   │   │   ├── DetailView.tsx
   │   │   │   ├── MetadataPanel.tsx
   │   │   │   └── IframeEmbed.tsx
   │   │   └── Layout/
   │   │       ├── Sidebar.tsx
   │   │       └── Header.tsx
   │   ├── pages/
   │   │   ├── DashboardPage.tsx
   │   │   ├── BrowserPage.tsx
   │   │   └── DetailPage.tsx
   │   ├── hooks/
   │   │   ├── useStats.ts
   │   │   ├── useTechnologies.ts
   │   │   └── useTechnology.ts
   │   ├── api/
   │   │   └── client.ts
   │   └── App.tsx
   ├── package.json
   ├── vite.config.ts
   └── tailwind.config.js
   ```

2. **Dashboard Page:**
   - Overview cards: Total technologies, Universities tracked, Fields covered, Latest scrape
   - Bar chart: Technologies by top field (clickable to filter)
   - Pie chart: Distribution by university (top 10 + "Other")
   - Line chart: Technologies added over time (by first_seen)
   - Optional: Geographic coverage visualization

3. **Technology Browser Page:**
   - Left sidebar: Filters (field dropdown, university multi-select, date range, search box)
   - Main area: Sortable data table with columns:
     - Title, University, Field, Subfield, First Seen, Actions
   - Click row → navigate to detail page
   - Cross-filtering: clicking chart elements updates table filters

4. **Technology Detail Page:**
   - Top section: Title, university, classification badge
   - Metadata panel:
     - Field/Subfield with confidence score
     - Patent geography (tags)
     - Keywords (tags)
     - Dates (first seen, last updated)
   - Description section: Full text with formatting
   - Action buttons:
     - "View Original" → opens URL in new tab
     - "Embed View" → toggles iframe panel showing original site
   - Raw data accordion (collapsible JSON viewer)

### Phase 3: Integration

1. **Development workflow:**
   - Backend: `tech-scraper serve --reload` on port 8000
   - Frontend: `npm run dev` on port 5173 with proxy to backend

2. **Production build:**
   - `npm run build` → outputs to `web/dist/`
   - FastAPI serves static files from `web/dist/`
   - Single command: `tech-scraper serve` serves both API and frontend

3. **Docker integration:**
   - Add `web` service to docker-compose.yml
   - Or bundle frontend build into scraper container

## File Changes Summary

**New files:**
- `src/api/main.py` - FastAPI application
- `src/api/routes/stats.py` - Statistics endpoints
- `src/api/routes/technologies.py` - Technology endpoints
- `src/api/schemas.py` - Response models
- `web/` - Entire React frontend directory

**Modified files:**
- `src/cli.py` - Add `serve` command
- `requirements.txt` - Add fastapi, uvicorn
- `docker-compose.yml` - Optional web service

## Key Design Decisions

1. **Hybrid iframe approach:** Show scraped data prominently, with a toggle button to reveal an iframe embedding the original university URL. This gives users quick access to stored data while allowing deep-dive into the source.

2. **Cross-filtering:** Charts on dashboard are interactive - clicking a bar/slice filters the technology list, enabling drill-down from analytics to specific records.

3. **No authentication:** Internal use only, served on localhost. Can add auth later if needed.

4. **Responsive design:** Tailwind CSS for mobile-friendly layout, though primary use is desktop.

5. **API-first:** Clean separation allows future mobile app or other clients.

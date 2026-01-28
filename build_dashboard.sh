#!/bin/bash
# Ralph Wiggum Style Build Loop
# "I'm helping!"
#
# Usage:
#   ./build_dashboard.sh        - Show current step
#   ./build_dashboard.sh done   - Mark current step complete
#   ./build_dashboard.sh status - Show all steps
#   ./build_dashboard.sh reset  - Start over

PROGRESS_FILE=".dashboard_progress"

STEPS=(
  "api-setup"
  "api-stats"
  "api-technologies"
  "api-cli"
  "web-scaffold"
  "web-api-client"
  "web-layout"
  "web-dashboard"
  "web-browser"
  "web-detail"
  "web-integration"
  "production"
)

# Initialize progress file if it doesn't exist
if [[ ! -f "$PROGRESS_FILE" ]]; then
  echo "0" > "$PROGRESS_FILE"
fi

current_step=$(cat "$PROGRESS_FILE")

show_step() {
  local step_num=$1
  local step_name=${STEPS[$step_num]}

  echo ""
  echo "=============================================="
  echo "  Step $((step_num + 1))/${#STEPS[@]}: $step_name"
  echo "=============================================="
  echo ""

  case $step_name in
    "api-setup")
      cat << 'EOF'
Create the FastAPI application skeleton.

FILES TO CREATE:
  src/api/__init__.py
  src/api/main.py

REQUIREMENTS:
  - FastAPI app with CORS middleware (allow localhost origins)
  - Health check endpoint: GET /api/health -> {"status": "ok"}
  - Import and use existing database.py for DB connection

TEST:
  pip install fastapi uvicorn
  uvicorn src.api.main:app --reload
  curl http://localhost:8000/api/health

PROMPT FOR CLAUDE:
  "Create a FastAPI app at src/api/main.py with CORS for localhost and a
   /api/health endpoint. Use the existing database setup from src/database.py"
EOF
      ;;

    "api-stats")
      cat << 'EOF'
Add statistics/analytics endpoints.

FILES TO CREATE:
  src/api/routes/__init__.py
  src/api/routes/stats.py
  src/api/schemas.py (Pydantic models)

ENDPOINTS:
  GET /api/stats/overview
    -> {total_technologies, total_universities, total_fields, last_scrape}

  GET /api/stats/by-field
    -> [{top_field, count, subfields: [{subfield, count}]}]

  GET /api/stats/by-university
    -> [{university, count, last_scraped}]

  GET /api/stats/timeline
    -> [{month: "2024-01", count}] (by first_seen)

TEST:
  curl http://localhost:8000/api/stats/overview
  curl http://localhost:8000/api/stats/by-field

PROMPT FOR CLAUDE:
  "Add stats API routes to src/api/routes/stats.py with endpoints for
   overview, by-field, by-university, and timeline. Create Pydantic
   schemas in src/api/schemas.py. Query the technologies table."
EOF
      ;;

    "api-technologies")
      cat << 'EOF'
Add technology listing and detail endpoints.

FILES TO CREATE/MODIFY:
  src/api/routes/technologies.py
  src/api/schemas.py (add more models)

ENDPOINTS:
  GET /api/technologies
    Query params: page, limit, q (search), top_field, subfield,
                  university, from_date, to_date
    -> {items: [...], total, page, pages}

  GET /api/technologies/{uuid}
    -> Full technology object with all fields

  GET /api/taxonomy
    -> Field/subfield hierarchy for filter dropdowns

TEST:
  curl "http://localhost:8000/api/technologies?limit=10"
  curl "http://localhost:8000/api/technologies?top_field=Robotics"
  curl http://localhost:8000/api/taxonomy

PROMPT FOR CLAUDE:
  "Add technology endpoints to src/api/routes/technologies.py - paginated
   list with filters, single item by UUID, and taxonomy endpoint. Use
   full-text search for the 'q' parameter."
EOF
      ;;

    "api-cli")
      cat << 'EOF'
Add 'serve' command to the CLI.

FILES TO MODIFY:
  src/cli.py
  requirements.txt (add fastapi, uvicorn)

COMMAND:
  tech-scraper serve [--host HOST] [--port PORT] [--reload]

BEHAVIOR:
  - Starts uvicorn with the FastAPI app
  - Default: 127.0.0.1:8000
  - --reload for development

TEST:
  tech-scraper serve --reload
  # In another terminal:
  curl http://localhost:8000/api/health

PROMPT FOR CLAUDE:
  "Add a 'serve' command to src/cli.py that runs uvicorn with the
   FastAPI app from src/api/main. Add fastapi and uvicorn to requirements.txt"
EOF
      ;;

    "web-scaffold")
      cat << 'EOF'
Create the React project with Vite and Tailwind.

COMMANDS TO RUN:
  cd /Users/alexrudd/Scholomance
  npm create vite@latest web -- --template react-ts
  cd web
  npm install
  npm install -D tailwindcss postcss autoprefixer
  npx tailwindcss init -p
  npm install react-router-dom recharts @tanstack/react-table

FILES TO CONFIGURE:
  web/tailwind.config.js - Add content paths
  web/src/index.css - Add Tailwind directives
  web/vite.config.ts - Add proxy to localhost:8000

TEST:
  cd web && npm run dev
  # Opens http://localhost:5173

PROMPT FOR CLAUDE:
  "Set up a React + Vite + TypeScript project in ./web with Tailwind CSS.
   Configure vite proxy to forward /api to localhost:8000. Install
   react-router-dom, recharts, and @tanstack/react-table."
EOF
      ;;

    "web-api-client")
      cat << 'EOF'
Create API client and React hooks for data fetching.

FILES TO CREATE:
  web/src/api/client.ts - Fetch wrapper
  web/src/api/types.ts - TypeScript interfaces matching backend schemas
  web/src/hooks/useStats.ts - Hook for stats endpoints
  web/src/hooks/useTechnologies.ts - Hook for tech list with filters
  web/src/hooks/useTechnology.ts - Hook for single tech by UUID

REQUIREMENTS:
  - client.ts: Base fetch with error handling, JSON parsing
  - Types should match the Pydantic schemas from backend
  - Hooks use useState/useEffect, handle loading/error states

TEST:
  Import and use hooks in App.tsx, verify data loads

PROMPT FOR CLAUDE:
  "Create API client at web/src/api/client.ts and TypeScript types
   matching the FastAPI schemas. Create React hooks for useStats,
   useTechnologies (with filter params), and useTechnology."
EOF
      ;;

    "web-layout")
      cat << 'EOF'
Build the app shell with navigation.

FILES TO CREATE:
  web/src/components/Layout/Sidebar.tsx
  web/src/components/Layout/Header.tsx
  web/src/components/Layout/Layout.tsx
  web/src/pages/DashboardPage.tsx (placeholder)
  web/src/pages/BrowserPage.tsx (placeholder)
  web/src/pages/DetailPage.tsx (placeholder)
  web/src/App.tsx (with routing)

REQUIREMENTS:
  - Sidebar: Navigation links (Dashboard, Browse Technologies)
  - Header: App title, maybe search
  - Layout: Wraps pages with sidebar + header
  - Routes: /, /browse, /technology/:uuid
  - Tailwind styling: Clean, minimal, professional

TEST:
  Navigate between Dashboard and Browse pages

PROMPT FOR CLAUDE:
  "Create layout components in web/src/components/Layout with sidebar
   navigation and header. Set up React Router in App.tsx with routes
   for dashboard (/), browser (/browse), and detail (/technology/:uuid).
   Use Tailwind for styling."
EOF
      ;;

    "web-dashboard")
      cat << 'EOF'
Build the analytics dashboard page.

FILES TO CREATE:
  web/src/components/Dashboard/OverviewCards.tsx
  web/src/components/Dashboard/FieldChart.tsx
  web/src/components/Dashboard/UniversityChart.tsx
  web/src/components/Dashboard/TimelineChart.tsx
  web/src/pages/DashboardPage.tsx (full implementation)

REQUIREMENTS:
  - OverviewCards: 4 stat cards (total techs, universities, fields, last scrape)
  - FieldChart: Bar chart of technologies by top_field (using Recharts)
  - UniversityChart: Pie chart of top 10 universities
  - TimelineChart: Line chart of techs by month
  - All charts clickable to navigate to /browse with filter applied

TEST:
  Dashboard displays real data from API
  Clicking a bar navigates to filtered browse view

PROMPT FOR CLAUDE:
  "Build the dashboard page with overview cards and Recharts visualizations.
   FieldChart (bar), UniversityChart (pie), TimelineChart (line). Make
   charts clickable to navigate to /browse with the appropriate filter."
EOF
      ;;

    "web-browser")
      cat << 'EOF'
Build the technology browser with filters and table.

FILES TO CREATE:
  web/src/components/Browser/FilterPanel.tsx
  web/src/components/Browser/TechnologyTable.tsx
  web/src/components/Browser/Pagination.tsx
  web/src/pages/BrowserPage.tsx (full implementation)

REQUIREMENTS:
  - FilterPanel: Dropdowns (field, subfield, university), date range, search box
  - TechnologyTable: Using @tanstack/react-table
    Columns: Title, University, Field, Subfield, First Seen
    Sortable columns, clickable rows
  - Pagination: Page controls, items per page selector
  - URL state: Filters should sync with URL query params
  - Read filter from URL on load (for dashboard click-through)

TEST:
  Browse page shows technologies
  Filters work and update URL
  Navigate from dashboard chart -> browse with filter applied

PROMPT FOR CLAUDE:
  "Build the technology browser page with FilterPanel, TechnologyTable
   (using @tanstack/react-table), and Pagination. Sync filters with
   URL query params so dashboard links work."
EOF
      ;;

    "web-detail")
      cat << 'EOF'
Build the technology detail page with iframe toggle.

FILES TO CREATE:
  web/src/components/Detail/DetailView.tsx
  web/src/components/Detail/MetadataPanel.tsx
  web/src/components/Detail/IframeEmbed.tsx
  web/src/pages/DetailPage.tsx (full implementation)

REQUIREMENTS:
  - Header: Title, university badge, classification badge
  - MetadataPanel: Field/subfield, confidence, geography tags, keywords, dates
  - Description: Full text, formatted
  - IframeEmbed: Toggle button to show/hide iframe of original URL
  - "Open Original" button -> new tab
  - Raw data section (collapsible JSON viewer)
  - Back button to return to browse

TEST:
  Click technology from browse -> see detail
  Toggle iframe shows original site
  Back button preserves browse filters

PROMPT FOR CLAUDE:
  "Build the detail page showing technology info with MetadataPanel,
   description, and an IframeEmbed component that can be toggled to
   show the original URL. Include 'Open Original' link and back nav."
EOF
      ;;

    "web-integration")
      cat << 'EOF'
Wire up cross-filtering and polish.

FILES TO MODIFY:
  Various components as needed

REQUIREMENTS:
  - Dashboard charts update a shared filter state
  - Clicking chart -> navigate to browse with filter
  - Loading states with spinners
  - Empty states with helpful messages
  - Error states with retry option
  - Responsive layout tweaks
  - Keyboard navigation where appropriate

TEST:
  Full user flow: Dashboard -> click chart -> browse filtered ->
  click row -> detail -> iframe -> back to browse (filters preserved)

PROMPT FOR CLAUDE:
  "Polish the dashboard with cross-filtering, loading/error/empty states,
   and ensure the full user flow works: dashboard -> browse -> detail -> back."
EOF
      ;;

    "production")
      cat << 'EOF'
Configure production build and static serving.

FILES TO MODIFY:
  src/api/main.py - Serve static files from web/dist
  web/vite.config.ts - Production build config
  docker-compose.yml - Optional web service

REQUIREMENTS:
  - npm run build -> outputs to web/dist
  - FastAPI serves web/dist as static files at /
  - API routes remain at /api/*
  - Single command: tech-scraper serve (serves both)

TEST:
  cd web && npm run build
  tech-scraper serve
  # Open http://localhost:8000 -> loads React app
  # API still works at /api/*

PROMPT FOR CLAUDE:
  "Configure FastAPI to serve the React production build from web/dist
   as static files. The app should work from a single 'tech-scraper serve'
   command in production mode."
EOF
      ;;

    *)
      echo "Unknown step: $step_name"
      ;;
  esac

  echo ""
  echo "----------------------------------------------"
  echo "When done, run: ./build_dashboard.sh done"
  echo "----------------------------------------------"
}

show_status() {
  echo ""
  echo "Dashboard Build Progress"
  echo "========================"
  echo ""
  for i in "${!STEPS[@]}"; do
    if [[ $i -lt $current_step ]]; then
      echo "  [x] $((i + 1)). ${STEPS[$i]}"
    elif [[ $i -eq $current_step ]]; then
      echo "  [>] $((i + 1)). ${STEPS[$i]}  <-- CURRENT"
    else
      echo "  [ ] $((i + 1)). ${STEPS[$i]}"
    fi
  done
  echo ""
  echo "Progress: $current_step/${#STEPS[@]} steps completed"
  echo ""
}

mark_done() {
  if [[ $current_step -ge ${#STEPS[@]} ]]; then
    echo ""
    echo "All steps completed! Dashboard is ready."
    echo ""
    exit 0
  fi

  echo ""
  echo "Marked '${STEPS[$current_step]}' as complete."
  current_step=$((current_step + 1))
  echo "$current_step" > "$PROGRESS_FILE"

  if [[ $current_step -ge ${#STEPS[@]} ]]; then
    echo ""
    echo "=============================================="
    echo "  ALL STEPS COMPLETED!"
    echo "  Your dashboard is ready to use."
    echo ""
    echo "  Start it with: tech-scraper serve"
    echo "  Open: http://localhost:8000"
    echo "=============================================="
  else
    echo "Next step: ${STEPS[$current_step]}"
    echo ""
    echo "Run ./build_dashboard.sh to see instructions."
  fi
}

reset_progress() {
  echo "0" > "$PROGRESS_FILE"
  echo "Progress reset. Starting from step 1."
}

# Main
case "${1:-}" in
  "done")
    mark_done
    ;;
  "status")
    show_status
    ;;
  "reset")
    reset_progress
    ;;
  *)
    if [[ $current_step -ge ${#STEPS[@]} ]]; then
      echo ""
      echo "All steps completed! Dashboard is ready."
      echo "Run './build_dashboard.sh reset' to start over."
      echo ""
    else
      show_step $current_step
    fi
    ;;
esac

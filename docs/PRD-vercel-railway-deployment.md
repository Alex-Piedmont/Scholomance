# PRD: Deploy Scholomance to Vercel + Railway

**Version:** 1.1
**Date:** 2026-03-02
**Author:** Product Management
**Status:** Draft
**Project:** Scholomance -- University Tech Transfer Platform

---

## 1. Introduction / Overview

Scholomance currently runs entirely on localhost: a Vite dev server on port 5173, a FastAPI backend on port 8001, and a local PostgreSQL database. There is no public URL. This PRD covers the minimal work to ship the platform to the web using Vercel (frontend) and Railway (backend + database), relying on each platform's native hobby-tier features rather than writing custom infrastructure.

The target state: a publicly accessible React SPA on Vercel that talks to a FastAPI API hosted on Railway, backed by Railway's managed PostgreSQL. Scrapers continue running locally via CLI, connecting to the Railway database over its public endpoint. After migration, the Railway database is the single source of truth -- no local database sync.

---

## 2. Goals

- **Public URL:** The platform is accessible on the internet at a Vercel-provided domain (and optionally a custom domain later).
- **Zero custom infra code:** Use Vercel's native Vite support and Railway's native Docker support. No Terraform, no custom CI/CD pipelines.
- **Minimal code changes:** Under 50 lines of application code changed total across frontend and backend.
- **Local scraper workflow preserved:** `python -m src.cli scrape` continues working from a local machine, pointed at the Railway database.
- **Auto-deploy on push:** Both Vercel and Railway deploy automatically when code is pushed to main.

### What Success Looks Like

A user navigates to the Vercel URL, sees the dashboard, browses technologies, and views detail pages -- all served from production infrastructure. The developer runs scrapers locally against the Railway database, and new data appears on the live site.

---

## 3. User Stories

### US-1: Public Access

**As a** visitor, **I want to** access the tech transfer dashboard via a public URL, **so that** I can browse university technologies without needing localhost setup.

**Acceptance Criteria:**
- [ ] Vercel deployment serves the React SPA at a `.vercel.app` domain
- [ ] All client-side routes (/, /browser, /technologies/:uuid, /opportunities) resolve correctly via SPA fallback
- [ ] API calls from the frontend reach the Railway-hosted backend and return data
- [ ] CORS preflight (OPTIONS) requests succeed for all endpoints including POST `/api/opportunities/:uuid/assess`

### US-2: Local Scraping to Production DB

**As a** developer, **I want to** run scrapers locally against the Railway PostgreSQL, **so that** new data appears on the live site without deploying scraper code.

**Acceptance Criteria:**
- [ ] `DATABASE_URL` env var in local `.env` points at Railway's public PostgreSQL URL with `?sslmode=require`
- [ ] `python -m src.cli scrape --university stanford --limit 1` succeeds against the remote DB
- [ ] Scraped data appears on the live Vercel frontend

### US-3: Backend Health Monitoring

**As a** developer, **I want** Railway to monitor the health of the FastAPI service, **so that** it restarts on failure.

**Acceptance Criteria:**
- [ ] Railway health check hits `/api/health` and gets a 200 response
- [ ] `/api/health/db` returns HTTP 503 (not 200) when the database is unreachable
- [ ] `/api/health/db` returns HTTP 200 with `technologies_count` when the database is healthy

---

## 4. Functional Requirements

### Frontend (Vercel)

- **FR-1:** Add `web/vercel.json` with SPA rewrite rule (catch-all to `index.html`).

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

- **FR-2:** Update `web/src/api/client.ts` line 17 to read the API base URL from an environment variable, falling back to `/api` for local development.

```typescript
const API_BASE = import.meta.env.VITE_API_URL || '/api'
```

This is the only line that changes in client.ts. All existing `fetchJson` and `postJson` calls continue to work because they already use `${API_BASE}${endpoint}`.

**URL path verification:** With `VITE_API_URL=https://<railway>.up.railway.app/api`, the resulting request URLs will be `https://<railway>.up.railway.app/api/stats/overview`, `https://<railway>.up.railway.app/api/technologies`, etc. This matches the backend router prefixes (`/api/stats`, `/api`, `/api`).

- **FR-3:** Vercel project configuration (done via Vercel CLI or dashboard, not code):

| Setting | Value |
|---|---|
| Root Directory | `web` |
| Framework Preset | Vite |
| Build Command | `npm run build` (default) |
| Output Directory | `dist` (default) |
| Environment Variable | `VITE_API_URL` = `https://<railway-backend>.up.railway.app/api` |

- **FR-4:** Connect GitHub repo to Vercel for auto-deploy on push to main.

### Backend (Railway)

- **FR-5:** Update CORS in `src/api/main.py` to support Vercel production domain and preview deployment URLs via wildcard pattern.

```python
import os
import re

cors_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

# Add production frontend URL if configured
frontend_url = os.environ.get("FRONTEND_URL")
if frontend_url:
    cors_origins.append(frontend_url)

# Allow Vercel preview deployments
cors_origin_regex = os.environ.get("CORS_ORIGIN_REGEX")
```

Use FastAPI's `allow_origin_regex` parameter for preview deploy support:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,  # e.g. r"https://.*\.vercel\.app"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,  # Cache preflight responses for 1 hour
)
```

- **FR-6:** Fix `/api/health/db` to return proper HTTP status codes.

```python
from fastapi.responses import JSONResponse

@app.get("/api/health/db")
def db_health_check():
    try:
        count = db.count_technologies()
        return {"status": "ok", "technologies_count": count}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": str(e)}
        )
```

- **FR-7:** Create a lightweight `Dockerfile.railway` for the API-only service (no Playwright, no scraper dependencies):

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY src/ ./src/
COPY pyproject.toml .
COPY setup.py .
RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

Note: The `CMD` uses shell form to interpolate Railway's `$PORT` env var. The `web/` directory is intentionally NOT copied to prevent the SPA catch-all route in `main.py` from activating.

- **FR-8:** Create `requirements-api.txt` with only the dependencies needed for the API service:

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.25
psycopg2-binary>=2.9.9
alembic>=1.13.1
pydantic>=2.6.1
pydantic-settings>=2.1.0
python-dotenv>=1.0.1
anthropic>=0.18.1
python-dateutil>=2.8.2
pytz>=2024.1
loguru>=0.7.2
```

This excludes Playwright, beautifulsoup4, lxml, requests, APScheduler, schedule, and other scraper-only dependencies. Image size ~200MB vs ~500MB+.

- **FR-9:** Add `railway.toml` at project root to declaratively configure the build:

```toml
[build]
dockerfilePath = "Dockerfile.railway"

[deploy]
healthcheckPath = "/api/health"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

- **FR-10:** Railway environment variables (configured via Railway dashboard/CLI, not code):

| Variable | Value |
|---|---|
| `DATABASE_URL` | Auto-injected by Railway PostgreSQL addon |
| `ANTHROPIC_API_KEY` | User's API key (for on-demand assessment endpoint) |
| `FRONTEND_URL` | `https://<project>.vercel.app` |
| `CORS_ORIGIN_REGEX` | `https://.*\.vercel\.app` |
| `PORT` | Auto-injected by Railway |
| `LOG_LEVEL` | `INFO` |

- **FR-11:** Connect GitHub repo to Railway for auto-deploy on push to main.

### Database (Railway PostgreSQL)

- **FR-12:** Provision PostgreSQL via Railway's native addon (one click in dashboard or `railway add --plugin postgresql` via CLI). No custom code.

- **FR-13:** Migrate existing local data to Railway using full pg_dump/pg_restore (schema + data). Do NOT run Alembic first -- the dump includes the full schema.

```bash
# Export from local
pg_dump -Fc tech_transfer > scholomance.dump

# Import to Railway (use Railway's public DATABASE_URL)
pg_restore --no-owner --no-privileges -d "<railway-public-url>" scholomance.dump
```

Flags: `--no-owner` and `--no-privileges` are required because Railway uses different role names than the local database.

- **FR-14:** After initial data restore, verify Alembic migration state is correct:

```bash
DATABASE_URL="<railway-public-url>" alembic current
```

This should show the latest migration revision. Future schema changes use Alembic migrations run manually by the developer:

```bash
DATABASE_URL="<railway-public-url>" alembic upgrade head
```

Note: When running Alembic against Railway, ensure the local `.env` file does not contain a conflicting `DATABASE_URL` that would override the command-line value. Pydantic Settings loads `.env` by default. Either temporarily rename `.env` or use: `DOTENV_PATH=/dev/null DATABASE_URL="<url>" alembic upgrade head`.

### Database URL Scheme Normalization

- **FR-15:** Railway may inject `DATABASE_URL` with `postgres://` scheme. SQLAlchemy 2.0 requires `postgresql://`. Update `src/config.py` `get_database_url()` to normalize:

```python
def get_database_url(self) -> str:
    url = self.database_url
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url and "postgresql://" in url:
        return url
    return (
        f"postgresql://{self.postgres_user}:{self.postgres_password}"
        f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    )
```

---

## 5. Non-Goals (Out of Scope)

- **Custom domain setup:** Use the default `.vercel.app` and `.up.railway.app` domains initially.
- **Authentication / access control:** The site remains publicly accessible with no login.
- **Scraper deployment to cloud:** Scrapers stay local. No Railway service for scraping.
- **Scheduler deployment:** The cron/scheduler service is not deployed. Scrapes are manual.
- **Custom CI/CD pipelines:** Rely on Vercel and Railway native git-push deploys.
- **SSL certificate management:** Both Vercel and Railway provide SSL natively.
- **CDN / caching layer:** Not needed at this scale.
- **Monitoring / alerting beyond health checks:** No Datadog, Sentry, etc.
- **Database backups automation:** Railway provides basic backups on paid plans; no custom backup scripts.
- **Local/remote DB sync:** After migration, Railway is the single source of truth.
- **Vercel serverless functions or edge functions:** The frontend is a pure static SPA. No API routes on Vercel.

---

## 6. Design Considerations

### Architecture Diagram

```
                    Internet
                       |
         +-------------+-------------+
         |                           |
   [Vercel Hobby]            [Railway Starter]
   React SPA (Vite)          FastAPI + Uvicorn
   static CDN                Dockerfile.railway
   VITE_API_URL -----------> /api/* endpoints
                                    |
                             [Railway PostgreSQL]
                             (auto-injected DATABASE_URL)
                                    |
                             (public endpoint + SSL)
                                    |
                           [Local Machine]
                           CLI scrapers
                           Alembic migrations
```

### User Experience

No UX changes. The app looks and behaves identically to localhost. The only difference is the URL in the browser.

---

## 7. Technical Considerations

### Modified Files

| File | Current Size | Changes |
|---|---|---|
| `web/src/api/client.ts` | 131 lines | 1 line: `API_BASE` reads from `import.meta.env.VITE_API_URL` |
| `src/api/main.py` | 88 lines | ~12 lines: CORS reads env vars, add `allow_origin_regex`, health check returns 503 |
| `src/config.py` | 63 lines | ~3 lines: normalize `postgres://` to `postgresql://` in `get_database_url()` |

### New Files

| File | Purpose |
|---|---|
| `web/vercel.json` | SPA rewrite rules for Vercel (~5 lines) |
| `Dockerfile.railway` | Lightweight API-only Docker image, no Playwright (~15 lines) |
| `requirements-api.txt` | API-only Python dependencies (~12 lines) |
| `railway.toml` | Railway build/deploy configuration (~7 lines) |

### Performance

- **API cold start:** Railway Starter keeps services awake. No cold start concern on paid tier.
- **Frontend:** Vercel serves static assets from edge CDN globally. Sub-100ms TTFB for static files.
- **Database latency:** Railway PostgreSQL is co-located with the Railway service. Local scraper connections will have ~50-100ms latency to Railway (acceptable for batch scraping).
- **CORS preflight:** Cross-origin requests will incur an additional OPTIONS preflight request. Browser caches preflight for `Access-Control-Max-Age` seconds. Consider setting this header to 3600 (1 hour).

---

## 8. Security and Privacy

### Sensitive Data

- `ANTHROPIC_API_KEY` stored in Railway environment variables (encrypted at rest).
- `DATABASE_URL` with credentials stored in Railway environment variables.
- No secrets in code or version control.
- Railway PostgreSQL public endpoint uses SSL (`?sslmode=require` in connection string).

### CORS

- Production CORS: specific Vercel domain via `FRONTEND_URL` env var.
- Preview deploys: wildcard regex `https://.*\.vercel\.app` via `CORS_ORIGIN_REGEX` env var.
- Local development: hardcoded localhost origins preserved.

### Input Validation

- No new user inputs introduced. Existing FastAPI validation unchanged.
- The `VITE_API_URL` env var is build-time only (baked into the JS bundle), not runtime-configurable by end users.

---

## 9. Testing Strategy

### Smoke Tests (Post-Deploy)

- [ ] Vercel URL loads the dashboard with real data
- [ ] `/browser` page lists technologies with pagination
- [ ] `/technologies/:uuid` detail page renders correctly
- [ ] `/opportunities` page loads
- [ ] POST to `/api/opportunities/:uuid/assess` works (CORS preflight succeeds)
- [ ] `curl https://<railway>.up.railway.app/api/health` returns `{"status": "ok"}`
- [ ] `curl https://<railway>.up.railway.app/api/health/db` returns `{"status": "ok", "technologies_count": N}` where N > 0
- [ ] Local `python -m src.cli scrape --university stanford --limit 1` succeeds against Railway DB
- [ ] Scraped data appears on live Vercel frontend

### Regression

- [ ] Local development workflow still works (Vite dev server + local FastAPI + local PostgreSQL)
- [ ] `npm run build` in `web/` succeeds with and without `VITE_API_URL` set
- [ ] Existing Docker Compose setup still works for local development

---

## 10. Dependencies and Assumptions

### Dependencies

**No new libraries to install.** All required packages (FastAPI, uvicorn, SQLAlchemy, etc.) are already in `requirements.txt` and `pyproject.toml`.

### CLI Tools Needed (User Must Install)

| Tool | Install | Purpose |
|---|---|---|
| Vercel CLI | `npm i -g vercel` | Link repo, set env vars, initial deploy |
| Railway CLI | `npm i -g @railway/cli` | Provision PostgreSQL, set env vars, initial deploy |

### Assumptions

- The GitHub repository is accessible to both Vercel and Railway for git-push auto-deploys.
- Railway Starter tier ($5/mo) provides sufficient resources for the FastAPI service + PostgreSQL.
- Vercel Hobby tier (free) supports the static SPA with sufficient bandwidth (100GB/mo limit; no serverless functions used).
- The local `pg_dump` includes Alembic's `alembic_version` table, so migration state is preserved in the Railway DB.
- SMTP env vars (SMTP_HOST, SMTP_PORT, etc.) from docker-compose are NOT needed on Railway -- they are only used by the scheduler which is out of scope.

---

## 11. Implementation Order

| Phase | Scope | Risk Level | Verification |
|---|---|---|---|
| **Phase 1** | Code changes: update `client.ts`, `main.py` CORS + health check, `config.py` URL normalization, add `vercel.json`, `Dockerfile.railway`, `requirements-api.txt`, `railway.toml` | Low | `npm run build` succeeds, local dev still works |
| **Phase 2** | Railway: provision PostgreSQL, deploy FastAPI, pg_restore data, verify Alembic state | Medium | `curl /api/health/db` returns OK with correct count |
| **Phase 3** | Vercel: deploy frontend, set `VITE_API_URL`, verify SPA routing | Low | Dashboard loads with live data at Vercel URL |
| **Phase 4** | End-to-end: test all routes, test local scraper against Railway DB, verify CORS preflight for POST | Low | Full smoke test checklist passes |

---

## Resolved Questions

**Q1:** Use default `.vercel.app` / `.up.railway.app` domains. Custom domain deferred.

**Q2:** Add commented-out production env var templates to local `.env` (FRONTEND_URL, CORS_ORIGIN_REGEX, VITE_API_URL).

**Q3:** Set `Access-Control-Max-Age: 3600` (1 hour) on the CORS middleware via `max_age=3600` parameter.
